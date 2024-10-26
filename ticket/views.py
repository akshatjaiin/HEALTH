# django modules
from django.urls import reverse
from django.db import IntegrityError
from django.contrib.sessions.models import Session
from django.shortcuts import  render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse  

# import
import os
import json
from . import constants # some constants which we are using
from datetime import date
from dotenv import load_dotenv
from random import randint
# Import date class from datetime module
from datetime import date
from .models import User, Ticket # models to save in db 
from google.api_core import retry
import google.generativeai as genai
 
def get_date():
    # return current date
    return date.today() 

load_dotenv() # load env
genai.configure(api_key=os.getenv('GEMINI_API_KEY')) # cofiguring model api 

model_name = 'gemini-1.5-flash'

# Initialize the model with safety settings
model = genai.GenerativeModel(
    model_name, system_instruction=constants.MUSEUM_BOT_PROMPT, safety_settings=constants.SAFE, 
    generation_config= {'response_mime_type': "application/json"}
)

chat_history = []
chat_history.append({'role': 'user', 'parts': f"{[constants.MUSEUM_BOT_PROMPT]}"})
chat_history.append({'role': 'model', 'parts': ['OK I will fill response back to user to continue chat with him.']})

@retry.Retry(initial=5, maximum=3)  # Limiting retries to avoid long delays
def send_message(message,history) -> None:
    """Send a message to the conversation and return the response."""
    convo = model.start_chat(history=history)
    res = convo.send_message(message)
    history.extend([
        {'role': 'user', 'parts': message},
        {'role': 'model', 'parts': res.text}
    ])
    return res


def strToJSON(jsonStr: str,history):
    try:
        return json.loads(jsonStr)
    except Exception as err:
        print("ai sended a destructured response")
        print(jsonStr)
        res = strToJSON(send_message(f"[ERROR] '{jsonStr}'. Please follow the correct format described on the rule section.", history).text, history)
        return res
def makeValidJson(jsonData,history)->list:
    if isinstance(jsonData, dict):
        print("Dict Detected, handling...")
        jsonData = [jsonData]
    if(not jsonData[0].get("your_response_back_to_user",False)):
        return makeValidJson(strToJSON(f"[ERROR] you dont send the your_response_back_to_user pls refer rules and send the response , your prev res -> {jsonData}",history),history)
    return jsonData


@login_required(login_url='login')
def index(request):
    if request.method == "POST":
        # Handle changing user's preferred language
        if language := request.POST.get("language"):
            request.user.language = language
            request.user.save()
            return HttpResponseRedirect(reverse("index"))

        # Handle input form submission
        user_input = request.POST.get("user_input", "").strip()
        if not user_input:
            return JsonResponse({"status": 400, "message": "Bad request", "successful": False})

        session_id = request.POST.get("session_id")
        response = send_message(user_input,request.session[session_id])
        print(f"user: {user_input}")
        print(f"ai json: {response.text}")
        # Parse the AI response and ensure valid JSON
        response_json = strToJSON(response.text,request.session[session_id])
        response_json = makeValidJson(response_json,request.session[session_id])

        res_data = {}
        if response_json and response_json[0].get("confirm"):
            ticket_details = {}
            for user_data in response_json[0]["users"]:
                user_info = user_data['user_info']
                name = user_info.get('name')
                age = user_info.get('age')
                indian = user_info.get('indian')
                insurance = user_info.get('insurance')
                disease = user_info.get('disease')
                day = user_info.get('day')
                month = user_info.get('month')
                year = user_info.get('year')

                # Check for missing fields
                fields = {'name': name, 'age': age, 'indian': indian, 'insurance': insurance, 'disease': disease, 'day': day, 'month': month, 'year': year}
                missing_field = next((field for field, value in fields.items() if value is None), None)
                if missing_field:
                    print(f"Missing field: {missing_field}")
                    response = send_message(f"Message from system: 'Please ask for {missing_field}. You cannot book a ticket without it.'",request.session[session_id])


                    response_json = strToJSON(response.text,request.session[session_id])
                    response_json = makeValidJson(response_json,request.session[session_id])
                    return JsonResponse({
                        "status": 200,
                        "user_input": user_input,
                        "response": response.text,
                    })

                # Convert to date object
                try:
                    book_date = date(year, month, day)
                except ValueError:
                    return JsonResponse({"status": 400, "message": "Invalid date provided", "successful": False})

                # Save the ticket
                ticket = Ticket(
                    name=name,
                    age=age,
                    indian=indian,
                    insurance=insurance,
                    disease=disease,
                    date=book_date,
                    owner=request.user,
                    paid=False
                )
                ticket.save()

                # Calculate the ticket price
                ticket_details[ticket.id] = ticket.total_cost

            res_data['confirm'] = True
            res_data['ticketDetails'] = ticket_details

        res_data.update({
            "status": 200,
            "user_input": user_input,
            "response": response_json,
            "successful": True,
            "message": "AI response fetched successfully",
        })

        # Update session history and save it
        request.session["chat_history"].extend([
            {'role': 'user', 'parts': user_input},
            {'role': 'model', 'parts': response.text}
        ])
        request.session.modified = True

        return JsonResponse(res_data)

    elif request.method == "GET":
        # Simplified initial introduction message
        # Initialize 'chat_history' if it doesn't exist
        request.session.setdefault("chat_history", [])
        session_id = str(randint(1,9)*randint(1,9))
        request.session[session_id] = chat_history
        user_prompt = f"""[Hi, myself {request.user}. I don't want to scedule,
                            I just want to know about you. My preferred language is {request.user.language}. 
                            Although I hate cringy emojis, you can use them to improve the creativity of your response.
                            Please only use my preferred language, even if I use another language to talk with you.
                            I hate when someone asks me more than one detail in a response. 
                            I just want to know what you can do in a concise way.
                            I might repeat the same prompt again and again, 
                            just remind me if I do that and use different reminders each time.]"""
        if 'prompt' in request.GET:
            user_prompt = request.GET['prompt'] + f",language:{request.user.language}"

        response = send_message(user_prompt,request.session[session_id])

        print(f"AI first response: {response.text}")
        response_json = makeValidJson(strToJSON(response.text,request.session[session_id]),request.session[session_id])
        request.session.modified = True
        print(request.session,session_id)
        return render(request, "ticket/index.html", {"firstResponse": response_json[0].get("your_response_back_to_user", "Hi",),"session_id":session_id})

    else:
        return JsonResponse({"message": "Method not allowed", "status": 405})

 # elif request.method == "GET":
        # Send an initial introduction message in the user's preferred language
        # # user_prompt = 

        

# creating a ticket url for every ticket so that user can acess those
@login_required(login_url='login')
def ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    year = ticket.date.year
    month = ticket.date.month
    day = ticket.date.day

    return render(request, "ticket/ticket.html", {
        "name": ticket.name,
        "age": ticket.age,
        "indian": ticket.indian,
        "insurance": ticket.insurance,
        "ticket_id": ticket.id,
        "day": day,
        "month": month,
        "year": year,
        "disease": ticket.disease,
    })


@login_required(login_url='login')
def makepaymentsuccess(request):
    if request.method == "POST":
        tickets = json.loads(request.body.decode('utf-8'))
        print("ticket conf , tickets:",tickets,type(tickets))
        for ticket_id in tickets["tickets"]:
            ticket = Ticket.objects.get(id=int(ticket_id))
            ticket.paid = True # mark the tickets paid if payment is successful
            ticket.save()
        return JsonResponse({"status": 200, "successful": Ticket.objects.get(id=tickets["tickets"][0]).paid})
    return JsonResponse({"message":"Method not allowed","status":405}) 

def login_view(request):
    if request.method == "POST":
        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        # Check if authentication successful
        if user is not None:
            login(request, user) # login the user
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "ticket/login.html", {
                "message": "Invalid username and/or password."
            })

    return render(request, "ticket/login.html")
    

def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"] 

        if password != confirmation:
            return render(request, "ticket/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "ticket/register.html", {
                "message": "username already taken."
            })
        # make user login
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    return render(request, "ticket/register.html")

def about_museum(request):
    return render(request, "ticket/about_museum.html")


def booked(request):
    tickets = Ticket.objects.filter(paid=True, owner=request.user)
    return render(request, "ticket/booked.html", {"tickets": tickets})

def about(request):
    return render(request, "ticket/about.html")

def soon(request):
    return render(request, "ticket/soon.html")

def thankyou(request):
    return render(request, "ticket/thankyou.html")
