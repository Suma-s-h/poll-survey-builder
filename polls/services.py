import random
from collections import defaultdict

from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone

from .models import Poll, PollActivity, UserProfile, Vote


def log_activity(poll, activity_type, actor=None, message=''):
    return PollActivity.objects.create(
        poll=poll, activity_type=activity_type, actor=actor, message=message,
    )


def get_or_create_profile(user):
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            'avatar_color': random.choice(UserProfile.AVATAR_COLORS),
            'follower_count': random.randint(5, 200),
            'following_count': random.randint(5, 150),
        },
    )
    return profile


def get_related_polls(poll, limit=4):
    if not poll.category:
        return Poll.objects.none()
    return (
        Poll.objects.filter(category=poll.category, is_public=True)
        .exclude(pk=poll.pk)
        .select_related('creator', 'category')
        .prefetch_related('questions__choices')[:limit]
    )


def get_poll_history(poll, limit=20):
    return poll.activities.select_related('actor')[:limit]


def get_recent_votes(poll, limit=10):
    return poll.votes.select_related('choice', 'voter')[:limit]


def get_dashboard_stats():
    now = timezone.now()
    total_polls = Poll.objects.count()
    draft_polls = Poll.objects.filter(status=Poll.STATUS_DRAFT).count()
    closed_polls = Poll.objects.filter(
        Q(status=Poll.STATUS_CLOSED) | Q(status=Poll.STATUS_ACTIVE, end_date__lt=now)
    ).count()
    active_polls = total_polls - draft_polls - closed_polls
    total_responses = Vote.objects.count()
    participants = Vote.objects.values('voter_id', 'session_key').distinct().count()
    today_votes = Vote.objects.filter(created_at__date=timezone.localdate()).count()
    return {
        'total_polls': total_polls,
        'active_polls': active_polls,
        'closed_polls': closed_polls,
        'draft_polls': draft_polls,
        'total_responses': total_responses,
        'participants': participants,
        'today_votes': today_votes,
    }


def get_analytics_summary():
    stats = get_dashboard_stats()
    total_polls = stats['total_polls']
    total_users = User.objects.count()

    avg_responses_per_poll = round(stats['total_responses'] / total_polls, 1) if total_polls else 0

    polls = list(Poll.objects.all())
    if polls and total_users:
        rates = [poll.participant_count / total_users * 100 for poll in polls]
        avg_participation_rate = round(sum(rates) / len(rates), 1)
    else:
        avg_participation_rate = 0

    most_popular = Poll.objects.annotate(responses=Count('votes')).order_by('-responses').first()
    newest = Poll.objects.order_by('-created_at').first()

    return {
        'total_polls': total_polls,
        'total_responses': stats['total_responses'],
        'participants': stats['participants'],
        'avg_responses_per_poll': avg_responses_per_poll,
        'avg_participation_rate': avg_participation_rate,
        'most_popular_poll': most_popular.title if most_popular else '—',
        'most_popular_poll_votes': most_popular.total_votes if most_popular else 0,
        'newest_poll': newest.title if newest else '—',
        'newest_poll_date': newest.created_at if newest else None,
    }


def get_analytics_data():
    now = timezone.now()
    cutoff = now - timezone.timedelta(days=13)
    month_cutoff = now - timezone.timedelta(days=365)

    votes_per_day_qs = (
        Vote.objects.filter(created_at__date__gte=cutoff.date())
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    votes_by_day = {row['day'].isoformat(): row['count'] for row in votes_per_day_qs}
    votes_per_day = []
    for offset in range(13, -1, -1):
        day = (now - timezone.timedelta(days=offset)).date()
        votes_per_day.append({'label': day.strftime('%b %d'), 'value': votes_by_day.get(day.isoformat(), 0)})

    participant_rows = Vote.objects.filter(created_at__date__gte=cutoff.date()).annotate(
        day=TruncDate('created_at')
    ).values('day', 'voter_id', 'session_key')
    day_participants = defaultdict(set)
    for row in participant_rows:
        day_participants[row['day']].add((row['voter_id'], row['session_key']))
    daily_active_participants = []
    for offset in range(13, -1, -1):
        day = (now - timezone.timedelta(days=offset)).date()
        daily_active_participants.append({
            'label': day.strftime('%b %d'),
            'value': len(day_participants.get(day, ())),
        })

    responses_per_poll = list(
        Poll.objects.annotate(responses=Count('votes'))
        .order_by('-responses')[:10]
        .values('title', 'responses')
    )

    most_popular_polls = list(
        Poll.objects.annotate(responses=Count('votes'))
        .filter(responses__gt=0)
        .order_by('-responses')[:10]
        .values('title', 'responses')
    )

    stats = get_dashboard_stats()
    status_distribution = [
        {'label': 'Active', 'value': stats['active_polls']},
        {'label': 'Closed', 'value': stats['closed_polls']},
        {'label': 'Draft', 'value': stats['draft_polls']},
    ]

    polls_by_month_qs = (
        Poll.objects.filter(created_at__gte=month_cutoff)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id', distinct=True))
        .order_by('month')
    )
    polls_by_month = {row['month'].strftime('%Y-%m'): row['count'] for row in polls_by_month_qs}
    monthly_labels = []
    monthly_polls = []
    cursor = month_cutoff.replace(day=1)
    seen = set()
    while cursor <= now:
        key = cursor.strftime('%Y-%m')
        if key not in seen:
            seen.add(key)
            monthly_labels.append(cursor.strftime('%b %Y'))
            monthly_polls.append(polls_by_month.get(key, 0))
        year = cursor.year + (1 if cursor.month == 12 else 0)
        month = 1 if cursor.month == 12 else cursor.month + 1
        cursor = cursor.replace(year=year, month=month)
    # Keep only the trailing 6 months for a readable chart.
    monthly_labels = monthly_labels[-6:]
    monthly_polls = monthly_polls[-6:]

    votes_by_category = list(
        Vote.objects.filter(poll__category__isnull=False)
        .values('poll__category__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    most_active_users = list(
        Vote.objects.exclude(voter=None)
        .values('voter__username')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )

    return {
        'votes_per_day': votes_per_day,
        'daily_active_participants': daily_active_participants,
        'responses_per_poll': responses_per_poll,
        'most_popular_polls': most_popular_polls,
        'status_distribution': status_distribution,
        'monthly_labels': monthly_labels,
        'monthly_polls': monthly_polls,
        'votes_by_category': votes_by_category,
        'most_active_users': most_active_users,
    }


def get_profile_stats(user):
    polls_created = user.polls.count()
    votes_submitted = Vote.objects.filter(voter=user).count()
    polls_participated = Vote.objects.filter(voter=user).values('poll_id').distinct().count()
    total_polls = Poll.objects.count()
    participation_rate = round((polls_participated / total_polls) * 100, 1) if total_polls else 0

    favorite = (
        Vote.objects.filter(voter=user, poll__category__isnull=False)
        .values('poll__category__name')
        .annotate(count=Count('id'))
        .order_by('-count')
        .first()
    )
    favorite_category = favorite['poll__category__name'] if favorite else None

    responses_received = Vote.objects.filter(poll__creator=user).count()

    most_popular = user.polls.annotate(responses=Count('votes')).order_by('-responses').first()
    most_popular_poll = most_popular.title if most_popular and most_popular.responses else None

    distinct_categories_voted = (
        Vote.objects.filter(voter=user, poll__category__isnull=False)
        .values('poll__category').distinct().count()
    )

    achievements = [
        {'name': 'First Poll', 'description': 'Created your first poll', 'icon': 'bi-flag-fill',
         'earned': polls_created >= 1},
        {'name': 'Poll Creator', 'description': 'Created 5 or more polls', 'icon': 'bi-collection-fill',
         'earned': polls_created >= 5},
        {'name': 'Active Voter', 'description': 'Cast 10 or more votes', 'icon': 'bi-check2-circle',
         'earned': votes_submitted >= 10},
        {'name': 'Power Voter', 'description': 'Cast 50 or more votes', 'icon': 'bi-lightning-fill',
         'earned': votes_submitted >= 50},
        {'name': 'Popular Creator', 'description': 'One of your polls received 50+ votes', 'icon': 'bi-trophy-fill',
         'earned': bool(most_popular and most_popular.responses >= 50)},
        {'name': 'Category Explorer', 'description': 'Voted across 3 or more categories', 'icon': 'bi-compass-fill',
         'earned': distinct_categories_voted >= 3},
    ]

    return {
        'polls_created': polls_created,
        'votes_submitted': votes_submitted,
        'polls_participated': polls_participated,
        'participation_rate': participation_rate,
        'favorite_category': favorite_category,
        'responses_received': responses_received,
        'most_popular_poll': most_popular_poll,
        'achievements': achievements,
    }
