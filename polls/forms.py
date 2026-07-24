from django import forms

from .models import Category, Comment, Poll, Question


class PollForm(forms.ModelForm):
    class Meta:
        model = Poll
        fields = [
            'title', 'description', 'category', 'status', 'start_date', 'end_date',
            'is_public', 'allow_multiple_choice', 'anonymous_voting',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Favorite team lunch spot'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional description shown to voters'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'end_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_multiple_choice': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'anonymous_voting': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['start_date'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['end_date'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['category'].required = False
        self.fields['end_date'].required = False


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text']
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Question text'}),
        }


class ChoiceForm(forms.Form):
    text = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choice text'}),
    )


class BaseChoiceFormSet(forms.BaseFormSet):
    def clean(self):
        if any(self.errors):
            return
        filled = [form for form in self.forms if form.cleaned_data.get('text', '').strip()]
        if len(filled) < 2:
            raise forms.ValidationError('Please provide at least two choices for this question.')


# extra=4 gives new questions a sensible starting point; the "Add another option"
# button in question_form.html grows this to an unlimited number client-side.
ChoiceFormSet = forms.formset_factory(ChoiceForm, formset=BaseChoiceFormSet, extra=4)


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2, 'placeholder': 'Share your thoughts on this poll...',
            }),
        }


class PollFilterForm(forms.Form):
    q = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Search by question, category, or creator...'
    }))
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'Any status')] + Poll.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    visibility = forms.ChoiceField(
        required=False,
        choices=[('', 'Any visibility'), ('public', 'Public'), ('private', 'Private')],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    category = forms.ModelChoiceField(
        required=False,
        queryset=Category.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
