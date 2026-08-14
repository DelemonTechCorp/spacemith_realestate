from django.core.management.base import BaseCommand
from blogs.models import BlogPost
from blogs.utils import clean_blog_content

class Command(BaseCommand):
    help = "Cleans old blog posts that have inline styles"

    def handle(self, *args, **options):
        count = 0
        for post in BlogPost.objects.all():
            cleaned = clean_blog_content(post.content)
            if cleaned != post.content:
                BlogPost.objects.filter(pk=post.pk).update(content=cleaned)
                count += 1
        self.stdout.write(self.style.SUCCESS(f"Cleaned {count} post(s)."))