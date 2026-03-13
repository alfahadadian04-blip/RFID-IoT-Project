from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def classes(request):
    return render(request, 'classes.html')