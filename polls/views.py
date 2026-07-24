import csv

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, F, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ChoiceFormSet, CommentForm, PollFilterForm, PollForm, QuestionForm
from .models import Category, Choice, Poll, PollActivity, Question, Vote
from .services import (
    get_analytics_data, get_analytics_summary, get_dashboard_stats, get_or_create_profile,
    get_poll_history, get_profile_stats, get_related_polls, get_recent_votes, log_activity,
)


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, f'Welcome, {user.username}! Your account has been created.')
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


def dashboard(request):
    stats = get_dashboard_stats()
    recent_activities = PollActivity.objects.select_related('poll', 'actor')[:10]
    return render(request, 'dashboard.html', {
        'stats': stats,
        'recent_activities': recent_activities,
    })


def _visible_polls_queryset(request):
    qs = Poll.objects.select_related('creator', 'category').prefetch_related('questions__choices')
    if request.user.is_authenticated:
        return qs.filter(Q(is_public=True) | Q(creator=request.user))
    return qs.filter(is_public=True)


def poll_list(request):
    filter_form = PollFilterForm(request.GET or None)
    polls = _visible_polls_queryset(request)

    if filter_form.is_valid():
        data = filter_form.cleaned_data
        if data.get('q'):
            term = data['q']
            polls = polls.filter(
                Q(title__icontains=term)
                | Q(category__name__icontains=term)
                | Q(creator__username__icontains=term)
            )
        if data.get('status'):
            polls = polls.filter(status=data['status'])
        if data.get('visibility') == 'public':
            polls = polls.filter(is_public=True)
        elif data.get('visibility') == 'private':
            polls = polls.filter(is_public=False)
        if data.get('category'):
            polls = polls.filter(category=data['category'])
        if data.get('date_from'):
            polls = polls.filter(created_at__date__gte=data['date_from'])
        if data.get('date_to'):
            polls = polls.filter(created_at__date__lte=data['date_to'])

    return render(request, 'poll_list.html', {'polls': polls, 'filter_form': filter_form})


def _get_owned_poll(request, pk):
    poll = get_object_or_404(Poll, pk=pk)
    if poll.creator_id != request.user.id:
        raise PermissionDenied('You do not have permission to manage this poll.')
    return poll


def _get_viewable_poll(request, pk):
    poll = get_object_or_404(Poll.objects.select_related('creator', 'category'), pk=pk)
    if not poll.is_public and poll.creator_id != getattr(request.user, 'id', None):
        raise PermissionDenied('This poll is private.')
    return poll


@login_required
def poll_create(request):
    if request.method == 'POST':
        form = PollForm(request.POST)
        if form.is_valid():
            poll = form.save(commit=False)
            poll.creator = request.user
            poll.save()
            log_activity(poll, PollActivity.TYPE_CREATED, actor=request.user, message=f'"{poll.title}" was created.')
            messages.success(request, 'Poll created successfully.')
            return redirect('question_create', pk=poll.pk)
    else:
        form = PollForm(initial={'status': Poll.STATUS_ACTIVE, 'start_date': timezone.now()})
    return render(request, 'poll_form.html', {'form': form, 'is_edit': False})


@login_required
def poll_edit(request, pk):
    poll = _get_owned_poll(request, pk)
    if request.method == 'POST':
        form = PollForm(request.POST, instance=poll)
        if form.is_valid():
            form.save()
            log_activity(poll, PollActivity.TYPE_UPDATED, actor=request.user, message=f'"{poll.title}" was updated.')
            messages.success(request, 'Poll updated.')
            return redirect('poll_detail', pk=poll.pk)
    else:
        form = PollForm(instance=poll)
    return render(request, 'poll_form.html', {'form': form, 'is_edit': True, 'poll': poll})


@login_required
def poll_manage(request, pk):
    poll = _get_owned_poll(request, pk)
    questions = poll.questions.prefetch_related('choices')
    return render(request, 'poll_manage.html', {'poll': poll, 'questions': questions})


def poll_detail(request, pk):
    poll = _get_viewable_poll(request, pk)

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to comment.')
            return redirect(f"/accounts/login/?next={request.path}")
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.poll = poll
            comment.author = request.user
            comment.save()
            messages.success(request, 'Comment posted.')
            return redirect(f"{request.path}#comments")
    else:
        comment_form = CommentForm()

    viewed_polls = request.session.get('viewed_polls', [])
    if poll.pk not in viewed_polls:
        Poll.objects.filter(pk=poll.pk).update(view_count=F('view_count') + 1)
        poll.view_count += 1
        viewed_polls.append(poll.pk)
        request.session['viewed_polls'] = viewed_polls

    questions = list(poll.questions.prefetch_related('choices'))
    for question in questions:
        ranked = sorted(question.choices.all(), key=lambda c: c.votes, reverse=True)
        question.winner = ranked[0] if ranked and ranked[0].votes > 0 else None

    return render(request, 'poll_detail.html', {
        'poll': poll,
        'questions': questions,
        'participant_count': poll.participant_count,
        'is_owner': poll.creator_id == getattr(request.user, 'id', None),
        'share_url': request.build_absolute_uri(),
        'related_polls': get_related_polls(poll),
        'recent_votes': get_recent_votes(poll),
        'poll_history': get_poll_history(poll),
        'comments': poll.comments.select_related('author'),
        'comment_form': comment_form,
    })


@login_required
def question_create(request, pk):
    poll = _get_owned_poll(request, pk)
    if request.method == 'POST':
        question_form = QuestionForm(request.POST)
        formset = ChoiceFormSet(request.POST, prefix='choices')
        if question_form.is_valid() and formset.is_valid():
            with transaction.atomic():
                question = question_form.save(commit=False)
                question.poll = poll
                question.save()
                for choice_form in formset:
                    text = choice_form.cleaned_data.get('text', '').strip()
                    if text:
                        Choice.objects.create(question=question, text=text)
            messages.success(request, 'Question added.')
            return redirect('poll_manage', pk=poll.pk)
    else:
        question_form = QuestionForm()
        formset = ChoiceFormSet(prefix='choices')
    return render(request, 'question_form.html', {
        'poll': poll,
        'question_form': question_form,
        'formset': formset,
    })


@login_required
@require_POST
def question_delete(request, pk, question_pk):
    poll = _get_owned_poll(request, pk)
    question = get_object_or_404(Question, pk=question_pk, poll=poll)
    question.delete()
    messages.success(request, 'Question deleted.')
    return redirect('poll_manage', pk=poll.pk)


@login_required
@require_POST
def poll_toggle_active(request, pk):
    poll = _get_owned_poll(request, pk)
    if poll.effective_status == Poll.STATUS_ACTIVE:
        poll.status = Poll.STATUS_CLOSED
        poll.save(update_fields=['status'])
        log_activity(poll, PollActivity.TYPE_CLOSED, actor=request.user, message=f'"{poll.title}" was closed.')
        messages.success(request, 'Poll is now closed.')
    else:
        poll.status = Poll.STATUS_ACTIVE
        poll.save(update_fields=['status'])
        messages.success(request, 'Poll is now open.')
    return redirect('poll_manage', pk=poll.pk)


@login_required
@require_POST
def poll_delete(request, pk):
    poll = _get_owned_poll(request, pk)
    messages.success(request, 'Poll deleted.')
    poll.delete()
    return redirect('poll_list')


def poll_vote(request, pk):
    poll = _get_viewable_poll(request, pk)
    questions = list(poll.questions.prefetch_related('choices'))
    voted_polls = request.session.get('voted_polls', [])

    if not poll.anonymous_voting and not request.user.is_authenticated:
        messages.info(request, 'Please log in to vote in this poll.')
        return redirect(f"/accounts/login/?next={request.path}")

    if not poll.is_open_for_voting:
        messages.info(request, 'This poll is closed. Here are the results so far.')
        return redirect('poll_results', pk=poll.pk)

    if poll.pk in voted_polls:
        messages.info(request, 'You have already voted in this poll.')
        return redirect('poll_results', pk=poll.pk)

    if not questions:
        messages.warning(request, 'This poll has no questions yet.')
        return redirect('poll_list')

    if request.method == 'POST':
        if not request.session.session_key:
            request.session.save()
        selections = {}
        missing = False
        for question in questions:
            if poll.allow_multiple_choice:
                choice_ids = request.POST.getlist(f'question_{question.pk}')
            else:
                value = request.POST.get(f'question_{question.pk}')
                choice_ids = [value] if value else []
            if choice_ids:
                selections[question.pk] = choice_ids
            else:
                missing = True

        if missing:
            messages.error(request, 'Please answer every question before submitting.')
        else:
            with transaction.atomic():
                for question in questions:
                    for choice_id in selections[question.pk]:
                        choice = get_object_or_404(Choice, pk=choice_id, question=question)
                        choice.votes += 1
                        choice.save(update_fields=['votes'])
                        Vote.objects.create(
                            poll=poll,
                            question=question,
                            choice=choice,
                            voter=request.user if request.user.is_authenticated else None,
                            session_key=request.session.session_key or '',
                        )
            log_activity(poll, PollActivity.TYPE_VOTE, actor=request.user if request.user.is_authenticated else None,
                         message='A new vote was submitted.')
            voted_polls.append(poll.pk)
            request.session['voted_polls'] = voted_polls
            messages.success(request, 'Vote submitted successfully.')
            return redirect('poll_results', pk=poll.pk)

    return render(request, 'poll_vote.html', {'poll': poll, 'questions': questions})


def poll_results(request, pk):
    poll = _get_viewable_poll(request, pk)
    questions = list(poll.questions.prefetch_related('choices'))

    for question in questions:
        ranked = sorted(question.choices.all(), key=lambda c: c.votes, reverse=True)
        question.ranked_choices = ranked
        question.winner = ranked[0] if ranked and ranked[0].votes > 0 else None

    all_choices = [choice for question in questions for choice in question.choices.all()]
    most_selected_option = max(all_choices, key=lambda c: c.votes, default=None)
    if most_selected_option and most_selected_option.votes == 0:
        most_selected_option = None

    total_users = User.objects.count()
    participation_rate = round(poll.participant_count / total_users * 100, 1) if total_users else 0
    average_votes = round(poll.total_votes / poll.total_options, 1) if poll.total_options else 0
    results_chart = [{'label': choice.text, 'votes': choice.votes} for choice in all_choices]

    return render(request, 'poll_results.html', {
        'poll': poll,
        'questions': questions,
        'participant_count': poll.participant_count,
        'participation_rate': participation_rate,
        'average_votes': average_votes,
        'most_selected_option': most_selected_option,
        'results_chart': results_chart,
    })


def poll_export_csv(request, pk):
    poll = _get_viewable_poll(request, pk)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="poll-{poll.pk}-results.csv"'
    writer = csv.writer(response)
    writer.writerow(['Question', 'Option', 'Votes', 'Percentage'])
    for question in poll.questions.prefetch_related('choices'):
        for choice in question.choices.all():
            writer.writerow([question.text, choice.text, choice.votes, choice.vote_percentage()])
    return response


def poll_export_json(request, pk):
    poll = _get_viewable_poll(request, pk)
    data = {
        'poll': {
            'title': poll.title,
            'description': poll.description,
            'category': poll.category.name if poll.category else None,
            'status': poll.effective_status,
            'created_at': poll.created_at.isoformat(),
            'end_date': poll.end_date.isoformat() if poll.end_date else None,
            'total_votes': poll.total_votes,
            'participants': poll.participant_count,
        },
        'questions': [
            {
                'text': question.text,
                'choices': [
                    {
                        'text': choice.text,
                        'votes': choice.votes,
                        'percentage': choice.vote_percentage(),
                    }
                    for choice in question.choices.all()
                ],
            }
            for question in poll.questions.prefetch_related('choices')
        ],
    }
    return JsonResponse(data)


def analytics(request):
    return render(request, 'analytics.html', {
        'stats': get_dashboard_stats(),
        'summary': get_analytics_summary(),
        'analytics': get_analytics_data(),
    })


@login_required
def profile(request):
    stats = get_profile_stats(request.user)
    user_profile = get_or_create_profile(request.user)
    polls_qs = request.user.polls.select_related('category')
    now = timezone.now()

    return render(request, 'profile.html', {
        'stats': stats,
        'user_profile': user_profile,
        'recent_polls': polls_qs[:10],
        'draft_polls': polls_qs.filter(status=Poll.STATUS_DRAFT),
        'closed_polls': polls_qs.filter(Q(status=Poll.STATUS_CLOSED) | Q(status=Poll.STATUS_ACTIVE, end_date__lt=now)),
        'recent_votes': Vote.objects.filter(voter=request.user).select_related('poll', 'choice')[:10],
        'recent_activity': PollActivity.objects.filter(actor=request.user).select_related('poll')[:10],
    })


@login_required
def profile_export_polls_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="my-polls.csv"'
    writer = csv.writer(response)
    writer.writerow(['Title', 'Category', 'Status', 'Created', 'Closing Date', 'Total Votes', 'Participants'])
    for poll in request.user.polls.select_related('category'):
        writer.writerow([
            poll.title,
            poll.category.name if poll.category else '',
            poll.effective_status,
            poll.created_at.isoformat(),
            poll.end_date.isoformat() if poll.end_date else '',
            poll.total_votes,
            poll.participant_count,
        ])
    return response


@login_required
def profile_export_polls_json(request):
    data = [{
        'title': poll.title,
        'category': poll.category.name if poll.category else None,
        'status': poll.effective_status,
        'created_at': poll.created_at.isoformat(),
        'end_date': poll.end_date.isoformat() if poll.end_date else None,
        'total_votes': poll.total_votes,
        'participants': poll.participant_count,
    } for poll in request.user.polls.select_related('category')]
    return JsonResponse({'polls': data})


@login_required
def profile_export_votes_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="my-voting-history.csv"'
    writer = csv.writer(response)
    writer.writerow(['Poll', 'Question', 'Choice', 'Voted At'])
    for vote in Vote.objects.filter(voter=request.user).select_related('poll', 'question', 'choice'):
        writer.writerow([vote.poll.title, vote.question.text, vote.choice.text, vote.created_at.isoformat()])
    return response


@login_required
def profile_export_votes_json(request):
    data = [{
        'poll': vote.poll.title,
        'question': vote.question.text,
        'choice': vote.choice.text,
        'voted_at': vote.created_at.isoformat(),
    } for vote in Vote.objects.filter(voter=request.user).select_related('poll', 'question', 'choice')]
    return JsonResponse({'votes': data})


def search(request):
    query = request.GET.get('q', '').strip()
    polls = users = categories = option_matches = []
    if query:
        polls = _visible_polls_queryset(request).filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )[:20]
        users = User.objects.filter(
            Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
        ).annotate(poll_count=Count('polls', distinct=True))[:20]
        categories = Category.objects.filter(name__icontains=query).annotate(
            poll_count=Count('polls', distinct=True)
        )[:20]
        visible_poll_ids = _visible_polls_queryset(request).values_list('pk', flat=True)
        option_matches = Choice.objects.filter(
            text__icontains=query, question__poll_id__in=visible_poll_ids
        ).select_related('question__poll')[:20]

    return render(request, 'search.html', {
        'query': query,
        'polls': polls,
        'users': users,
        'categories': categories,
        'option_matches': option_matches,
    })
