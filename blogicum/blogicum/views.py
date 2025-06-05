# blogicum/views.py

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.utils import timezone
from django.contrib.auth.views import LogoutView
from django.contrib.auth import logout

from blog.models import Post, User


def csrf_failure(request, reason=''):
    return render(request, 'pages/403csrf.html', status=403)


def page_not_found(request, exception):
    return render(request, 'pages/404.html', status=404)


def server_error(request):
    return render(request, 'pages/500.html', status=500)


class SignUpView(CreateView):
    form_class = UserCreationForm
    template_name = 'registration/registration_form.html'
    success_url = reverse_lazy('login')


pd = '-pub_date'


def profile_view(request, username):
    user = get_object_or_404(User, username=username)
    posts = Post.objects.filter(author=user, is_published=True,
                                pub_date__lte=timezone.now(),
                                category__is_published=True).order_by(pd)
    is_owner = request.user.is_authenticated and request.user == user
    return render(request, 'blog/profile.html', {
        'profile': user,
        'posts': posts,
        'is_owner': is_owner,
    })


class LogoutAllowGetView(LogoutView):
    def get(self, request, *args, **kwargs):
        from django.contrib.auth import logout
        logout(request)
        context = {'debug_logout': True}
        return render(request, 'registration/logged_out.html', context)


def logout_page(request):
    if request.user.is_authenticated:
        logout(request)
    return render(request, 'registration/logged_out.html')
