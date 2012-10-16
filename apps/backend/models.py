from django.db import models
from django.utils.translation import ugettext_lazy as _

from vocabulary import models as vocabularies


class AuthorityStat(models.Model):
    """
    Authority statistics.

    Keeping here only that statistics, calculation of which is time-consuming,
    and that is being calculated by triggers.
    """

    authority= models.ForeignKey(vocabularies.AuthorityProfile,
        )
    rank= models.IntegerField(default=0, verbose_name=u'Authority rank',
        help_text=_(u'Authority rank'))
