"""Tests for the fixed video categories and their migration."""

from django.core.exceptions import ValidationError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from rest_framework import serializers

from video_app.api.serializers import VideoListSerializer
from video_app.models import Video
from video_app.tests.helpers import TempMediaMixin, create_video

BEFORE_CHOICES = ("video_app", "0001_initial")
WITH_CHOICES = ("video_app", "0002_category_choices")


class CategoryChoiceTests(TempMediaMixin, TestCase):

    def test_existing_categories_are_valid_choices(self):
        for value in ("Action", "Animation", "Comedy", "Drama"):
            with self.subTest(category=value):
                self.assertIn(value, Video.Category.values)

    def test_values_equal_labels_so_the_api_output_is_unchanged(self):
        for value, label in Video.Category.choices:
            with self.subTest(category=value):
                self.assertEqual(value, label)
                self.assertNotIn(" ", value)

    def test_model_validation_rejects_unknown_category(self):
        video = create_video(category="Musical")
        with self.assertRaises(ValidationError) as context:
            video.full_clean()
        self.assertIn("category", context.exception.message_dict)

    def test_serializer_field_rejects_unknown_category(self):
        field = VideoListSerializer().fields["category"]
        self.assertEqual(field.run_validation("Drama"), "Drama")
        with self.assertRaises(serializers.ValidationError):
            field.run_validation("Musical")


class CategoryMigrationTests(TransactionTestCase):

    def test_migration_keeps_stored_categories(self):
        executor = MigrationExecutor(connection)
        executor.migrate([BEFORE_CHOICES])
        old_video = executor.loader.project_state(
            [BEFORE_CHOICES]).apps.get_model("video_app", "Video")
        video_id = old_video.objects.create(
            title="Film", description="Text", category="Comedy",
            video_file="videos/film.mp4",
        ).pk
        executor = MigrationExecutor(connection)
        executor.migrate([WITH_CHOICES])
        self.assertEqual(Video.objects.get(pk=video_id).category, "Comedy")
