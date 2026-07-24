from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class Poll(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_ACTIVE = 'active'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_CLOSED, 'Closed'),
    ]

    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='polls')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='polls',
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    is_public = models.BooleanField(default=True)
    allow_multiple_choice = models.BooleanField(default=False)
    anonymous_voting = models.BooleanField(default=True)
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('poll_manage', args=[self.pk])

    @property
    def total_votes(self):
        return sum(question.total_votes for question in self.questions.all())

    @property
    def total_options(self):
        return sum(question.choices.count() for question in self.questions.all())

    @property
    def effective_status(self):
        if self.status == self.STATUS_CLOSED:
            return self.STATUS_CLOSED
        if self.end_date and self.end_date < timezone.now():
            return self.STATUS_CLOSED
        return self.status

    @property
    def is_open_for_voting(self):
        return self.effective_status == self.STATUS_ACTIVE

    @property
    def participant_count(self):
        return (
            self.votes.values('voter_id', 'session_key')
            .distinct()
            .count()
        )


class Question(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='questions')
    text = models.CharField(max_length=300)

    def __str__(self):
        return self.text

    @property
    def total_votes(self):
        return sum(choice.votes for choice in self.choices.all())


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)

    def __str__(self):
        return self.text

    def vote_percentage(self):
        total = self.question.total_votes
        if not total:
            return 0
        return round((self.votes / total) * 100, 1)


class Vote(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='votes')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='votes')
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE, related_name='vote_records')
    voter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='votes_cast')
    session_key = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Vote for {self.choice} at {self.created_at:%Y-%m-%d %H:%M}'


class PollActivity(models.Model):
    TYPE_CREATED = 'created'
    TYPE_UPDATED = 'updated'
    TYPE_CLOSED = 'closed'
    TYPE_VOTE = 'vote_submitted'
    TYPE_CHOICES = [
        (TYPE_CREATED, 'Poll Created'),
        (TYPE_UPDATED, 'Poll Updated'),
        (TYPE_CLOSED, 'Poll Closed'),
        (TYPE_VOTE, 'Vote Submitted'),
    ]

    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    message = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Poll activities'

    def __str__(self):
        return f'{self.get_activity_type_display()} - {self.poll}'


class Comment(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    text = models.TextField(max_length=1000)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Comment by {self.author} on {self.poll}'


class UserProfile(models.Model):
    AVATAR_COLORS = ['primary', 'success', 'info', 'warning', 'danger', 'secondary']

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar_color = models.CharField(max_length=20, choices=[(c, c) for c in AVATAR_COLORS], default='primary')
    follower_count = models.PositiveIntegerField(default=0)
    following_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'Profile for {self.user.username}'

    @property
    def initials(self):
        first = (self.user.first_name or self.user.username)[:1]
        last = (self.user.last_name or '')[:1]
        return (first + last).upper() or self.user.username[:2].upper()
