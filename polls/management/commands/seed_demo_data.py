import random

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string

from faker import Faker

from polls.models import Category, Choice, Comment, Poll, PollActivity, Question, UserProfile, Vote
from polls.services import log_activity

fake = Faker()

CATEGORY_NAMES = ['Technology', 'Education', 'Business', 'Entertainment', 'Sports', 'Health', 'Programming']

DEMO_USER_COUNT = 150
DEMO_PASSWORD = 'DemoPass123!'

# (title, category, description, options, allow_multiple_choice, status, end_offset_days, is_public, weight)
POLL_SPECS = [
    (
        'Favorite Programming Language', 'Programming',
        'A quick pulse check on which language developers reach for most in their day-to-day work.',
        ['Python', 'JavaScript', 'Java', 'Go', 'Rust', 'C++'], False, Poll.STATUS_ACTIVE, 30, True, 1.4,
    ),
    (
        'Best Web Framework in 2026', 'Programming',
        'Frameworks evolve fast — which one do you think is leading the pack this year?',
        ['Django', 'Next.js', 'Laravel', 'Ruby on Rails', 'Spring Boot'], False, Poll.STATUS_ACTIVE, 45, True, 1.1,
    ),
    (
        'Remote vs Office Work', 'Business',
        'Understanding how our teams prefer to work as hybrid policies get revisited.',
        ['Fully Remote', 'Fully In-Office', 'Hybrid (3 days office)', 'Hybrid (1 day office)', 'No Preference'],
        False, Poll.STATUS_CLOSED, -10, True, 0.9,
    ),
    (
        'Favorite AI Assistant', 'Technology',
        'AI assistants are everywhere now — which one has earned a permanent spot in your workflow?',
        ['Claude', 'ChatGPT', 'Gemini', 'GitHub Copilot', 'Perplexity'], False, Poll.STATUS_ACTIVE, None, True, 1.3,
    ),
    (
        'Preferred Database', 'Programming',
        'From relational to document stores, tell us what powers your applications.',
        ['PostgreSQL', 'MySQL', 'SQLite', 'MongoDB', 'Redis', 'Oracle'], False, Poll.STATUS_ACTIVE, 20, True, 1.0,
    ),
    (
        'Frontend Framework Survey', 'Programming',
        'Select every frontend framework you have shipped to production with.',
        ['React', 'Vue', 'Angular', 'Svelte', 'Solid.js'], True, Poll.STATUS_ACTIVE, None, True, 1.2,
    ),
    (
        'Daily Coding Hours', 'Programming',
        'How much of your day is actually spent writing and reviewing code?',
        ['Less than 1 hour', '1-3 hours', '3-5 hours', '5-8 hours', 'More than 8 hours'],
        False, Poll.STATUS_CLOSED, -5, True, 0.8,
    ),
    (
        'Preferred Operating System', 'Technology',
        'The classic debate — what powers your daily driver machine?',
        ['Windows', 'macOS', 'Linux', 'ChromeOS'], False, Poll.STATUS_ACTIVE, None, True, 1.0,
    ),
    (
        'Favorite Streaming Service', 'Entertainment',
        'Where do you spend most of your streaming time these days?',
        ['Netflix', 'Disney+', 'Amazon Prime Video', 'HBO Max', 'YouTube Premium'],
        False, Poll.STATUS_ACTIVE, 60, True, 0.9,
    ),
    (
        'Preferred Exercise Routine', 'Health',
        'What keeps you active during a busy work week?',
        ['Weightlifting', 'Running', 'Yoga', 'Cycling', 'Swimming', 'None currently'],
        False, Poll.STATUS_ACTIVE, None, True, 0.8,
    ),
    (
        'Favorite Sport to Watch', 'Sports',
        'A new poll just launched — results will start rolling in soon.',
        ['Soccer / Football', 'Basketball', 'Cricket', 'Tennis', 'American Football'],
        False, Poll.STATUS_DRAFT, None, True, 0.0,
    ),
    (
        'Best Online Learning Platform', 'Education',
        'Internal survey for the L&D team — kept private while we finalize the report.',
        ['Coursera', 'Udemy', 'edX', 'Khan Academy', 'Pluralsight'], False, Poll.STATUS_ACTIVE, None, False, 0.6,
    ),
]


class Command(BaseCommand):
    help = 'Seed the database with realistic demo categories, polls, users, and votes.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush', action='store_true',
            help='Delete existing polls, categories, votes, and demo users before seeding.',
        )

    def handle(self, *args, **options):
        if options['flush']:
            self._flush()

        with transaction.atomic():
            categories = self._create_categories()
            demo_users = self._create_demo_users()
            polls = self._create_polls(categories, demo_users)
            total_votes, total_participants = self._create_votes(polls, demo_users)
            total_comments = self._create_comments(polls, demo_users)

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {len(categories)} categories, {len(demo_users)} demo users, '
            f'{len(polls)} polls, {total_votes} votes across ~{total_participants} participants, '
            f'{total_comments} comments.'
        ))

    def _flush(self):
        Poll.objects.all().delete()
        Category.objects.all().delete()
        User.objects.filter(username__startswith='demo_').delete()
        self.stdout.write('Cleared existing demo polls, categories, votes, and demo users.')

    def _create_categories(self):
        categories = {}
        for name in CATEGORY_NAMES:
            category, _ = Category.objects.get_or_create(name=name)
            categories[name] = category
        return categories

    def _create_demo_users(self):
        hashed_password = make_password(DEMO_PASSWORD)
        existing_usernames = set(User.objects.values_list('username', flat=True))
        new_users = []
        seen_usernames = set()
        while len(new_users) < DEMO_USER_COUNT:
            first_name = fake.first_name()
            last_name = fake.last_name()
            username = f'demo_{first_name.lower()}{random.randint(1000, 9999)}'
            if username in existing_usernames or username in seen_usernames:
                continue
            seen_usernames.add(username)
            new_users.append(User(
                username=username,
                email=f'{username}@example.com',
                password=hashed_password,
                first_name=first_name,
                last_name=last_name,
            ))
        User.objects.bulk_create(new_users)
        created_users = list(User.objects.filter(username__in=seen_usernames))

        UserProfile.objects.bulk_create([
            UserProfile(
                user=user,
                avatar_color=random.choice(UserProfile.AVATAR_COLORS),
                follower_count=random.randint(5, 250),
                following_count=random.randint(5, 180),
            )
            for user in created_users
        ])
        return created_users

    def _create_polls(self, categories, demo_users):
        polls = []
        now = timezone.now()
        for index, spec in enumerate(POLL_SPECS):
            title, category_name, description, options, multi_choice, status, end_offset, is_public, weight = spec
            creator = random.choice(demo_users)
            created_at = now - timezone.timedelta(days=random.randint(5, 85), hours=random.randint(0, 23))
            end_date = now + timezone.timedelta(days=end_offset) if end_offset is not None else None

            poll = Poll.objects.create(
                creator=creator,
                title=title,
                description=description,
                category=categories[category_name],
                status=status,
                start_date=created_at,
                end_date=end_date,
                is_public=is_public,
                allow_multiple_choice=multi_choice,
            )
            initial_views = int(random.randint(30, 90) * weight) if weight > 0 else random.randint(3, 15)
            Poll.objects.filter(pk=poll.pk).update(created_at=created_at, view_count=initial_views)
            poll.refresh_from_db()

            question = Question.objects.create(poll=poll, text=title)
            for option_text in options:
                Choice.objects.create(question=question, text=option_text)

            log_activity(poll, PollActivity.TYPE_CREATED, actor=creator, message=f'"{poll.title}" was created.')
            PollActivity.objects.filter(poll=poll, activity_type=PollActivity.TYPE_CREATED).update(created_at=created_at)

            if status == Poll.STATUS_CLOSED:
                closed_at = created_at + timezone.timedelta(days=random.randint(2, 10))
                closed_at = min(closed_at, now)
                activity = log_activity(poll, PollActivity.TYPE_CLOSED, actor=creator, message=f'"{poll.title}" was closed.')
                PollActivity.objects.filter(pk=activity.pk).update(created_at=closed_at)

            if index % 4 == 0 and status != Poll.STATUS_DRAFT:
                updated_at = created_at + timezone.timedelta(days=random.randint(1, 4))
                updated_at = min(updated_at, now)
                activity = log_activity(poll, PollActivity.TYPE_UPDATED, actor=creator, message=f'"{poll.title}" was updated.')
                PollActivity.objects.filter(pk=activity.pk).update(created_at=updated_at)

            polls.append((poll, weight, created_at))
        return polls

    def _create_votes(self, polls, demo_users):
        target_total_participants = random.randint(280, 340)
        weight_sum = sum(weight for _, weight, _ in polls) or 1

        today_bonus_pool = [p for p, weight, _ in polls if weight > 0]

        for poll, weight, created_at in polls:
            if weight <= 0:
                continue

            num_participants = max(5, round(target_total_participants * weight / weight_sum))
            choice_list = list(poll.questions.first().choices.all())
            choice_weights = [random.uniform(0.4, 3.0) for _ in choice_list]

            window_start = created_at
            window_end = timezone.now()

            for _ in range(num_participants):
                is_authenticated = random.random() < 0.7
                voter = random.choice(demo_users) if is_authenticated else None
                session_key = '' if is_authenticated else get_random_string(32)

                vote_time = fake.date_time_between(start_date=window_start, end_date=window_end, tzinfo=timezone.get_current_timezone())

                if poll.allow_multiple_choice:
                    pick_count = random.choices([1, 2, 3], weights=[0.5, 0.35, 0.15])[0]
                    picks = random.choices(choice_list, weights=choice_weights, k=min(pick_count, len(choice_list)))
                    picks = list(dict.fromkeys(picks))
                else:
                    picks = random.choices(choice_list, weights=choice_weights, k=1)

                for choice in picks:
                    choice.votes += 1
                    choice.save(update_fields=['votes'])
                    Vote.objects.create(
                        poll=poll, question=choice.question, choice=choice,
                        voter=voter, session_key=session_key, created_at=vote_time,
                    )

            sample_times = sorted(
                fake.date_time_between(start_date=window_start, end_date=window_end, tzinfo=timezone.get_current_timezone())
                for _ in range(min(3, num_participants))
            )
            for sample_time in sample_times:
                activity = log_activity(
                    poll, PollActivity.TYPE_VOTE, actor=None,
                    message=f'New votes recorded for "{poll.title}".',
                )
                PollActivity.objects.filter(pk=activity.pk).update(created_at=sample_time)

        self._add_todays_votes(today_bonus_pool, demo_users)
        today_votes = Vote.objects.filter(created_at__date=timezone.localdate()).count()
        total_votes = Vote.objects.count()
        total_participants = Vote.objects.values('voter_id', 'session_key').distinct().count()
        self.stdout.write(f"Today's votes seeded: {today_votes}")
        return total_votes, total_participants

    def _add_todays_votes(self, polls, demo_users):
        if not polls:
            return
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        for poll in random.sample(polls, k=min(4, len(polls))):
            choice_list = list(poll.questions.first().choices.all())
            choice_weights = [random.uniform(0.4, 3.0) for _ in choice_list]
            for _ in range(random.randint(5, 9)):
                is_authenticated = random.random() < 0.7
                voter = random.choice(demo_users) if is_authenticated else None
                session_key = '' if is_authenticated else get_random_string(32)
                vote_time = today_start + timezone.timedelta(
                    seconds=random.randint(0, max(1, int((now - today_start).total_seconds())))
                )
                choice = random.choices(choice_list, weights=choice_weights, k=1)[0]
                choice.votes += 1
                choice.save(update_fields=['votes'])
                Vote.objects.create(
                    poll=poll, question=choice.question, choice=choice,
                    voter=voter, session_key=session_key, created_at=vote_time,
                )

    def _create_comments(self, polls, demo_users):
        now = timezone.now()
        total_comments = 0
        for poll, weight, created_at in polls:
            if weight <= 0:
                continue
            for _ in range(random.randint(0, 5)):
                comment_time = fake.date_time_between(
                    start_date=created_at, end_date=now, tzinfo=timezone.get_current_timezone(),
                )
                Comment.objects.create(
                    poll=poll,
                    author=random.choice(demo_users),
                    text=fake.sentence(nb_words=random.randint(8, 16)),
                    created_at=comment_time,
                )
                total_comments += 1
        return total_comments
