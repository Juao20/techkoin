from django.db import models


class WeeklyReport(models.Model):
    """P4: the figures of one week for one shop and the text written from them."""

    shop = models.ForeignKey("accounts.Shop", on_delete=models.CASCADE, related_name="reports")
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    figures = models.JSONField(default=dict)
    summary = models.TextField(blank=True)
    actions = models.JSONField(default=list)
    used_ai = models.BooleanField(default=False)
    emailed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-period_end"]
        constraints = [
            models.UniqueConstraint(fields=["shop", "period_start"], name="one_report_per_week")
        ]

    def __str__(self):
        return f"Rapport {self.shop} {self.period_start:%d/%m/%Y}"
