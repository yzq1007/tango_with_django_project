from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from django.core.urlresolvers import reverse
from django.shortcuts import render
from rango.models import Category, Page
from rango.forms import CategoryForm, PageForm, UserForm, UserProfileForm
from django.contrib.auth.decorators import login_required
from datetime import datetime


def index(request):
    request.session.set_test_cookie()

    category_list = Category.objects.order_by('-likes')[:5]
    page_list = Page.objects.order_by('-views')[:5]
    context_dict = {'categories': category_list, 'pages': page_list,
                    'visits': request.session['visits']}
    visitor_cookie_handler(request)

    response = render(request, 'rango/index.html', context=context_dict)
    return response


def about(request):
    visitor_cookie_handler(request)
    context_dict = {'visits': request.session['visits']}
    return render(request, 'rango/about.html', context_dict)


def show_category(request, category_name_slug):
    context_dict = {}
    try:
        category = Category.objects.get(slug=category_name_slug)
        pages = Page.objects.filter(category=category)
        context_dict['pages'] = pages
        context_dict['category'] = category
    except Category.DoesNotExist:
        context_dict['pages'] = None
        context_dict['category'] = None
    return render(request, 'rango/category.html', context_dict)


def add_category(request):
    form = CategoryForm()
    context_dict = {}
    # A HTTP Method
    if request.method == 'POST':
        form = CategoryForm(request.POST)

        if form.is_valid():
            form.save(commit=True)
            return HttpResponseRedirect("/rango/")
        else:
            print(form.errors)
    context_dict['form'] = form

    return render(request, 'rango/add_category.html', context_dict)


# view for add_page.html
def add_page(request, category_name_slug):
    try:
        category = Category.objects.get(slug=category_name_slug)
    except Category.DoesNotExist:
        category = None
    form = PageForm()
    if request.method == 'POST':
        form = PageForm(request.POST)
        if form.is_valid():
            if category:
                page = form.save(commit=False)
                page.category = category
                page.views = 0
                page.save()
                return show_category(request, category_name_slug)
            else:
                print(form.errors)
    context_dict = {'form': form, 'category': category}
    return render(request, 'rango/add_page.html', context_dict)


def register(request):
    registered = False

    # if it is a HTTP POST, we are interested in processing data
    if request.method == 'POST':
        user_form = UserForm(data=request.POST)
        profile_form = UserProfileForm(data=request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            # save user's form data to dbase
            user = user_form.save()
            # hash password
            user.set_password(user.password)
            user.save()

            profile = profile_form.save(commit=False)
            profile.user = user

            # Get picture if provided
            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']
            # Save the UserProfile model instance
            profile.save()
            # Registration successful
            registered = True
        else:
            # Invalid forms
            print(user_form.errors, profile_form.errors)
    else:
        # Not a HTTP POST
        user_form = UserForm()
        profile_form = UserProfileForm()

    return render(request, 'rango/register.html', {'user_form': user_form,
                                                   'profile_form': profile_form,
                                                   'registered': registered})


def user_login(request):
    # pull out relevant information if it's HTTP POST
    if request.method == 'POST':
        # Gather username and password provided by the user.
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Check if valid
        user = authenticate(username=username, password=password)
        # If we have a user object, the details are correct
        if user:
            if user.is_active:
                # send user back to homepage
                login(request, user)
                return HttpResponseRedirect(reverse('index'))
            else:
                # an inactive account
                return HttpResponse("Your Rango account is disabled.")
        else:
            # bad login details provided
            print("Invalid login details:{0}, {1}".
                  format(username, password))
            return HttpResponse("Invalid login details supplied.")

    # Request is not HTTP POST
    else:
        # no context variable to pass to the template system
        return render(request, 'rango/login.html', {})


@login_required
def restricted(request):
    context_dict = {'message': "Since you're logged in, you can see this text!"}
    return render(request, 'rango/restricted.html', context_dict)


@login_required
def user_logout(request):
    logout(request)
    # Back to homepage
    return render(request, 'rango/index.html', {})  # HttpResponse(reverse('index'))


def visitor_cookie_handler(request):
    visits = int(get_server_side_cookie(request, 'visits', 1))
    last_visit_cookie = get_server_side_cookie(request,
                                               'last_visit', str(datetime.now()))
    last_visit_time = datetime.strptime(last_visit_cookie[:-7],
                                        '%Y-%m-%d %H:%M:%S')

    # If it's been more than a day since the last visit...
    if (datetime.now() - last_visit_time).days > 0:
        visits = visits + 1
        # Update the last visit cookie now that we have updated the count
        request.session['last_visit'] = str(datetime.now())
    else:
        # Set the last visit cookie
        request.session['last_visit'] = last_visit_cookie
    # Update/set the visits cookie
    request.session['visits'] = visits


# Helper method
def get_server_side_cookie(request, cookie, default_val=None):
    val = request.session.get(cookie)
    if not val:
        val = default_val
    return val
