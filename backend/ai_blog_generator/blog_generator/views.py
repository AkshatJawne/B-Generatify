from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
from pytube import YouTube
from .models import BlogPost
import os
import assemblyai as aai
import openai

import json


@login_required  # this decorator ensures that the user is logged in before accessing the index page
def index(request):
    return render(request, 'index.html')


@csrf_exempt  # this decorator ensures th at for the generate blog post request, there is no unnecessary csrf token check
def generate_blog(request):
    if request.method == "POST":
        try:
            # getting the youtube link from the request body
            data = json.loads(request.body)
            yt_link = data['link']
        except (KeyError, json.JSONDecodeError):
            # if the request body does not contain the link or there is an error decoding the json, return an error
            return JsonResponse({"error": "Invalid data sent"}, status=400)

        # getting the title of the youtube video
        title = yt_title(yt_link)

        # getting the transcription of the youtube video
        transcription = get_transcription(yt_link)
        if not transcription:
            return JsonResponse({"error": "Transcription failed"}, status=500)

        # generating the blog content from the transcription
        blog_content = generate_blog_from_transcription(transcription)
        if not blog_content:
            return JsonResponse({"error": "Failed to generate blog article"}, status=500)

        # saving the generated blog post to PostgresSQL database
        new_blog_article = BlogPost.objects.create(
            user=request.user,
            youtube_title="",
            youtube_link="",
            generated_content=""
        )

        return JsonResponse({"content": blog_content}, status=200)

    else:
        return JsonResponse({"error": "Invalid request method"}, status=405)


def yt_title(link):
    yt = YouTube(link)
    title = yt.title
    return title


def download_audio(link):
    # need to download the audio from the youtube video
    yt = YouTube(link)
    video = yt.streams.filter(only_audio=True).first()
    # download the video into new created out_file
    out_file = video.download(
        output_path=settings.MEDIA_ROOT, filename="audio")
    base, ext = os.path.splitext(out_file)
    new_file = base + '.mp3'  # convert to mp3 naming convention
    os.rename(out_file, new_file)  # rename the file
    return new_file


def get_transcription(link):
    # need to get the transcription from the youtube video
    audio_file = download_audio(link)
    aai.settings.api_key = "bd21c89d4a98424c91df274ccba5a187"
    # Create the transcriber
    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)

    return transcript.text


def generate_blog_from_transcription(transcription):
    openai.api_key = "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"
    # Create the prompt for the OpenAI API request
    prompt = f"Take on the roll of a professional writer. Based on the following transcript from a YouTube video, write a comprehensive blog article, based on the provided transcript, but write it such that it does not look like the description of a video, but rather, a proper blog article written by a professional blogger:\n\n{transcription}\n\nArticle:"

    response = openai.completion.create(
        model="text-davinci-003",
        prompt=prompt,
        max_tokens=100
    )

    # return the generated content from OpenAI
    generated_content = response.choices[0].text.strip()

    return generated_content


def user_login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        user = authenticate(request, username=username,
                            password=password)  # authenticating user using django's built in authenticate function

        if user is not None:
            # logging in user using django's built in login function
            login(request, user)
            return redirect('/')
        else:
            error_message = "Invalid username or password"
            return render(request, "login.html", {"error_message": error_message})
    return render(request, "login.html")


def user_signup(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]
        password = request.POST["password"]
        repeatpassword = request.POST["repeatpassword"]

        if password == repeatpassword:
            try:
                user = User.objects.create_user(
                    username=username, email=email, password=password)  # creating user
                user.save()  # saving user to django admin
                login(request, user)
                return redirect('/')
            except:
                error_message = "Error creating account"
                return render(request, "signup.html", {"error_message": error_message})
        else:
            error_message = "Passwords do not match"
            return render(request, "signup.html", {"error_message": error_message})
    return render(request, "signup.html")


def user_logout(request):
    logout(request)  # logging out user using django's built in logout function
    return redirect('/')
