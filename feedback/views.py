"""Complaint pages and success story pages."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from accounts import access
from accounts.mixins import RoleRequiredMixin, ScopedQuerysetMixin, role_required
from accounts.scoping import check_unit_in_scope

from . import services, stories
from .forms import ComplaintForm, ResponseForm, StoryCheckForm, StoryForm
from .models import Complaint, SuccessStory


class ComplaintListView(RoleRequiredMixin, ScopedQuerysetMixin, ListView):
    model = Complaint
    allowed_roles = access.roles_for("complaints")
    unit_field = "household__village"
    paginate_by = 25
    context_object_name = "complaints"

    def get_queryset(self):
        qs = super().get_queryset().select_related("household", "household__village")
        status, level = self.request.GET.get("status", ""), self.request.GET.get("level", "")
        if status in Complaint.Status.values:
            qs = qs.filter(status=status)
        elif status == "unresolved":
            qs = qs.exclude(status=Complaint.Status.RESOLVED)
        if level in Complaint.Level.values:
            qs = qs.filter(level=level)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = Complaint.Status.choices
        context["levels"] = Complaint.Level.choices
        return context


class ComplaintDetailView(RoleRequiredMixin, ScopedQuerysetMixin, DetailView):
    model = Complaint
    allowed_roles = access.roles_for("complaints")
    unit_field = "household__village"
    context_object_name = "complaint"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["responses"] = self.object.responses.select_related("responded_by")
        if services.can_handle(self.request.user, self.object):
            context["response_form"] = ResponseForm()
        return context


@require_POST
@role_required(*access.roles_for("respond_complaint"))
def respond_to_complaint(request, pk):
    complaint = get_object_or_404(Complaint.objects.select_related("household__village"), pk=pk)
    check_unit_in_scope(request.user, complaint.household.village)
    if not services.can_handle(request.user, complaint):
        messages.error(request, f"This complaint is with the {complaint.get_level_display().lower()} office, not yours.")
        return redirect("feedback:complaint_detail", pk=pk)
    form = ResponseForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Choose a status and write a response for the household.")
        return redirect("feedback:complaint_detail", pk=pk)
    services.respond(complaint, request.user, form.cleaned_data["message"], form.cleaned_data["status"])
    messages.success(request, "Response saved and sent to the household by SMS.")
    return redirect("feedback:complaint_detail", pk=pk)


class ComplaintCreateView(RoleRequiredMixin, CreateView):
    """A household raises a complaint about its own PDM experience."""

    form_class = ComplaintForm
    allowed_roles = access.roles_for("raise_complaint")
    template_name = "feedback/complaint_form.html"

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        # The role check comes first, so officials get "forbidden", not a redirect.
        if access.allows(user, "raise_complaint") and getattr(user, "household_record", None) is None:
            messages.error(request, "Your login is not linked to a household record yet. Ask your Parish Chief.")
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        complaint = services.raise_complaint(
            self.request.user.household_record,
            form.cleaned_data["category"],
            form.cleaned_data["description"],
            Complaint.Channel.WEB,
        )
        messages.success(self.request, f"Complaint received. Your reference is {complaint.reference}.")
        return redirect("my_household")


# Success stories


class StoryListView(RoleRequiredMixin, ScopedQuerysetMixin, ListView):
    model = SuccessStory
    allowed_roles = access.roles_for("stories")
    unit_field = "household__village"
    context_object_name = "stories"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related("household", "household__village")
        status = self.request.GET.get("status", "")
        return qs.filter(status=status) if status in SuccessStory.Status.values else qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = SuccessStory.Status.choices
        return context


class StoryFormMixin:
    model = SuccessStory
    form_class = StoryForm
    allowed_roles = access.roles_for("draft_story")
    template_name = "feedback/story_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        stories.record_consent(form.instance, self.request.user)
        response = super().form_valid(form)
        messages.success(self.request, "Story saved. Submit it to the PDC when the household has given consent.")
        return response

    def get_success_url(self):
        return reverse("feedback:story_detail", args=[self.object.pk])


class StoryCreateView(RoleRequiredMixin, StoryFormMixin, CreateView):
    def form_valid(self, form):
        form.instance.drafted_by = self.request.user
        return super().form_valid(form)


class StoryUpdateView(RoleRequiredMixin, ScopedQuerysetMixin, StoryFormMixin, UpdateView):
    unit_field = "household__village"

    def get_queryset(self):
        # Published or waiting stories are locked; send-backs and drafts can be edited.
        return super().get_queryset().filter(status__in=[SuccessStory.Status.DRAFT, SuccessStory.Status.REJECTED])


class StoryDetailView(RoleRequiredMixin, ScopedQuerysetMixin, DetailView):
    """The story beside the household's own records, so the PDC can check one against the other."""

    model = SuccessStory
    allowed_roles = access.roles_for("stories")
    unit_field = "household__village"
    context_object_name = "story"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        story, user = self.object, self.request.user
        editable = story.status in (SuccessStory.Status.DRAFT, SuccessStory.Status.REJECTED)
        context["can_edit"] = editable and access.allows(user, "draft_story")
        context["can_check"] = story.status == SuccessStory.Status.SUBMITTED and access.allows(user, "check_story")
        if context["can_check"]:
            context["check_form"] = StoryCheckForm()
        context["loans"] = story.household.loans.select_related("sacco", "disbursement").prefetch_related("repayments")
        return context


def _scoped_story(request, pk):
    story = get_object_or_404(SuccessStory.objects.select_related("household__village"), pk=pk)
    check_unit_in_scope(request.user, story.household.village)
    return story


@require_POST
@role_required(*access.roles_for("draft_story"))
def submit_story(request, pk):
    story = _scoped_story(request, pk)
    try:
        stories.submit(story, request.user)
    except stories.StoryError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "Story sent to the PDC to check.")
    return redirect("feedback:story_detail", pk=pk)


@require_POST
@role_required(*access.roles_for("check_story"))
def check_story(request, pk):
    story = _scoped_story(request, pk)
    form = StoryCheckForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Choose whether to approve the story or send it back.")
        return redirect("feedback:story_detail", pk=pk)
    data = form.cleaned_data
    try:
        stories.check(story, request.user, data["decision"] == "approve", data["note"], data["records_match"])
    except stories.StoryError as error:
        messages.error(request, str(error))
    else:
        if story.status == SuccessStory.Status.APPROVED:
            messages.success(request, "Story approved. It now appears on the public parish page.")
        else:
            messages.success(request, "Story sent back with your note.")
    return redirect("feedback:story_detail", pk=pk)
