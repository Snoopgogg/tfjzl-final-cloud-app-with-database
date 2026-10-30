from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.urls import reverse
from .models import Course, Enrollment, Question, Choice, Submission
import logging

logger = logging.getLogger(__name__)


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name,
                                            last_name=last_name, password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


def course_list_view(request):
    courses = Course.objects.order_by('-total_enrollment')[:10]
    for course in courses:
        if request.user.is_authenticated:
            course.is_enrolled = check_if_enrolled(request.user, course)
    context = {'course_list': courses}
    return render(request, 'onlinecourse/course_list_bootstrap.html', context)


def course_details_view(request, pk):
    context = {}
    course = get_object_or_404(Course, pk=pk)
    course.is_enrolled = check_if_enrolled(request.user, course)
    context['course'] = course
    return render(request, 'onlinecourse/course_details_bootstrap.html', context)


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user
    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()
    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


def submit(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user
    enrollment = Enrollment.objects.get(user=user, course=course)
    submission = Submission.objects.create(enrollment=enrollment)
    submitted_answers = extract_answers(request)
    for choice_id in submitted_answers:
        choice = get_object_or_404(Choice, pk=choice_id)
        submission.choices.add(choice)
    return HttpResponseRedirect(reverse(viewname='onlinecourse:show_exam_result', args=(course.id, submission.id,)))


def extract_answers(request):
    submitted_answers = []
    for key in request.POST:
        if key.startswith('choice'):
            value = request.POST.getlist(key)
            submitted_answers += [int(v) for v in value]
    return submitted_answers


def show_exam_result(request, course_id, submission_id):
    context = {}
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(Submission, pk=submission_id)
    selected_ids = submission.choices.values_list('id', flat=True)
    questions = Question.objects.filter(course=course)
    total_score = 0
    total_possible = 0
    for question in questions:
        total_possible += question.grade
        if question.is_get_score(selected_ids):
            total_score += question.grade
    if total_possible > 0:
        grade = int(total_score / total_possible * 100)
    else:
        grade = 0
    context['course'] = course
    context['grade'] = grade
    context['score'] = total_score
    context['total_possible'] = total_possible
    context['questions'] = questions
    context['selected_ids'] = selected_ids
    return render(request, 'onlinecourse/exam_result_bootstrap.html', context)
