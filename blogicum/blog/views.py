from django.shortcuts import render, get_object_or_404
from django.http import Http404
from django.utils import timezone
from .models import Post, Category, Comment
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django import forms
from django.db.models import Count

User = get_user_model()


def add_comment_count(queryset):
    return (queryset.annotate(comment_count=Count('comments'))
            .order_by('-pub_date'))


def get_page(queryset, request, per_page=10):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def published_posts(queryset):
    return queryset.filter(
        is_published=True,
        pub_date__lte=timezone.now(),
        category__is_published=True
    )


# Главная страница
def index(request):
    post_list = add_comment_count(Post.objects.filter(
        pub_date__lte=timezone.now(),
        is_published=True,
        category__is_published=True
    ))
    page_obj = get_page(post_list, request)
    context = {'page_obj': page_obj}
    return render(request, 'blog/index.html', context)


# Страница отдельной публикации
def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    is_owner = request.user.is_authenticated and request.user == post.author
    if (post.pub_date > timezone.now() or not post.
            is_published or not post.category.
            is_published) and not is_owner:
        raise Http404("Публикация недоступна.")
    form = CommentForm()
    comments = post.comments.select_related('author').all()
    context = {'post': post, 'form': form, 'comments': comments}
    return render(request, 'blog/detail.html', context)


# Страница категории
def category_posts(request, category_slug):
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True
    )
    post_list = add_comment_count(Post.objects.filter(
        category=category,
        is_published=True,
        pub_date__lte=timezone.now()
    ))
    page_obj = get_page(post_list, request)
    context = {
        'category': category,
        'page_obj': page_obj,
    }
    return render(request, 'blog/category.html', context)


# Страница профиля пользователя
def profile(request, username):
    user = get_object_or_404(User, username=username)
    # Только автор видит свои неопубликованные посты
    if request.user.is_authenticated and request.user == user:
        posts = add_comment_count(Post.objects.filter(author=user))
    else:
        posts = add_comment_count(published_posts(
            Post.objects.filter(author=user)))
    page_obj = get_page(posts, request)
    is_owner = request.user.is_authenticated and request.user == user
    context = {
        'profile': user,
        'page_obj': page_obj,
        'is_owner': is_owner,
    }
    return render(request, 'blog/profile.html', context)


# Заглушка для создания поста
def create_post(request):
    return render(request, 'blog/create.html')


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']


@login_required
def edit_profile(request, username):
    user = request.user
    if user.username != username:
        return redirect('blog:edit_profile', username=user.username)
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('blog:profile', username=user.username)
    else:
        form = ProfileEditForm(instance=user)
    return render(request, 'blog/user.html', {'form': form})


class PostCreateForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'text', 'image', 'category', 'location', 'pub_date']


@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostCreateForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('blog:profile', username=request.user.username)
    else:
        form = PostCreateForm()
    return render(request, 'blog/create.html', {'form': form})


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id=post.id)
    if request.method == 'POST':
        form = PostCreateForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            return redirect('blog:post_detail', post_id=post.id)
    else:
        form = PostCreateForm(instance=post)
    return render(request, 'blog/create.html',
                  {'form': form, 'is_edit': True, 'post': post})


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(
                attrs={'rows': 3, 'placeholder': 'Введите ваш комментарий...'}
            )
        }


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.post = post
            comment.save()
            return redirect('blog:post_detail', post_id=post.id)
    else:
        form = CommentForm()
    return render(request, 'blog/comment.html', {'form': form, 'post': post})


@login_required
def edit_comment(request, post_id, comment_id):
    post = get_object_or_404(Post, id=post_id)
    comment = get_object_or_404(Comment, id=comment_id, post=post)
    if comment.author != request.user:
        return redirect('blog:post_detail', post_id=post.id)
    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            return redirect('blog:post_detail', post_id=post.id)
    else:
        form = CommentForm(instance=comment)
    return render(request, 'blog/comment.html',
                  {'form': form, 'post': post, 'comment': comment})


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id=post.id)
    if request.method == 'POST':
        post.delete()
        return redirect('blog:profile', username=request.user.username)
    form = PostCreateForm(instance=post)
    return render(request, 'blog/create.html', {
        'form': form,
        'post': post,
        'is_delete': True,
    })


@login_required
def delete_comment(request, post_id, comment_id):
    post = get_object_or_404(Post, id=post_id)
    comment = get_object_or_404(Comment, id=comment_id, post=post)
    if comment.author != request.user:
        return redirect('blog:post_detail', post_id=post.id)
    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', post_id=post.id)
    return render(request, 'blog/comment.html',
                  {'form': None, 'post': post, 'comment':
                      comment, 'is_delete': True})
