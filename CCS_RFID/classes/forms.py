from django import forms

class MasterlistUploadForm(forms.Form):
    excel_file = forms.FileField(label='Select Excel file', help_text='.xlsx or .xls')