from django.contrib import admin

from .models import Category, Choice, Comment, Poll, PollActivity, Question, UserProfile, Vote

admin.site.site_header = 'Poll & Survey Builder Administration'
admin.site.site_title = 'Poll & Survey Builder'
admin.site.index_title = 'Manage polls, categories, votes, and users'


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 2


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'poll_count')
    search_fields = ('name',)

    def poll_count(self, obj):
        return obj.polls.count()


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = ('title', 'creator', 'category', 'status', 'is_public', 'created_at', 'total_votes')
    list_filter = ('status', 'category', 'is_public', 'allow_multiple_choice', 'created_at')
    search_fields = ('title', 'creator__username', 'category__name')
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'poll', 'total_votes')
    search_fields = ('text',)
    inlines = [ChoiceInline]


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ('text', 'question', 'votes')


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('poll', 'choice', 'voter', 'created_at')
    list_filter = ('poll', 'created_at')
    search_fields = ('poll__title', 'voter__username')
    date_hierarchy = 'created_at'


@admin.register(PollActivity)
class PollActivityAdmin(admin.ModelAdmin):
    list_display = ('poll', 'activity_type', 'actor', 'created_at')
    list_filter = ('activity_type', 'created_at')
    search_fields = ('poll__title',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('poll', 'author', 'text', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('poll__title', 'author__username', 'text')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'avatar_color', 'follower_count', 'following_count')
    search_fields = ('user__username',)
