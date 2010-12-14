from django.db import models

class Author(models.Model):
    name = models.CharField(max_length=100)

    def natural_key(self):
        return (self.name,)

class Book(models.Model):
    title = models.CharField(max_length=100)
    author = models.ForeignKey(Author)
