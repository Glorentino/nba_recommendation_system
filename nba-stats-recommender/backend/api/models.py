from django.db import models

class Player(models.Model):
    name = models.CharField(max_length=255)
    team = models.CharField(max_length=255)
    position = models.CharField(max_length=50)
    points = models.FloatField()
    assists = models.FloatField()
    rebounds = models.FloatField()

    def __str__(self):
        return self.name