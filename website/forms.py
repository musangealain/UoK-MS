from django import forms


class ApplicantInfoForm(forms.Form):
    full_name = forms.CharField(label="Full name", max_length=200)
    email = forms.EmailField(label="Email address")
    phone = forms.RegexField(
        label="Telephone number",
        regex=r'^[0-9+()\\-\\s]{7,20}$',
        error_messages={"invalid": "Enter a valid phone number."},
    )


class ProgramChoiceForm(forms.Form):
    program = forms.ChoiceField(
        label="Program",
        choices=[
            ("Computer Science", "Computer Science"),
            ("Business Administration", "Business Administration"),
            ("Engineering", "Engineering"),
            ("Health Sciences", "Health Sciences"),
            ("Law", "Law"),
        ],
    )
