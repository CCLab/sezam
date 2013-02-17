## The main concepts
### How it's all organized
All the project's applications are in `apps` directory:
- vocabulary: all the basic vocabularies, both abstract and real (for Authority Profiles, Categories, Territories and User Profiles). There is no views in this app, as it is only a descriptor of the models.
- authority: server-side logic for all the functions connected with Authorities (urlconf, views, forms, admin). The models for Authority Profiles are in the "vocabulary" app.
- userprofile: the same, but for User Profiles.
- pia_request: processing the requests to the Authorities. The biggest module, which includes everything listed above, but regarding the requests, as well as requests models and periodic tasks (checking email, marking outdated requests as "overdue" and "long-overdue").
- browser: server-side logic for the main (consolidated) page, as well as filter and search forms, and search indexes definitions.
- backend: context-processors, useful utilities, abstract classes for event-driven processes (such as those used in pia_request app).

### Key points in processing data
Before the request is sent it will always be stored in a draft (model PIARequestDraft). This goes not only to the requests, but also to the users' answers in the Thread of correspondence between a User and Authority.

There is a special type of Users - Trusted users. They differ from ordinary ones by possessing the ability to select several Authorities and send them one unified request. There will anyway be as many requests sent, as many Authorities picked up, but only one draft saved. That is why there is one-to-many relation between PIARequest and AuthorityProfile, but many-to-many relation between PIARequestDraft and AuthorityProfile.

### Subscriptions
Subscriptions are realized with the mechanism of "following" a particular entity: only Authority and Requests can be followed. In the current version only a registered user can follow an entity. A user can follow a particular Authority Profile and Request to this Authority, but in this case she/he will be receiving email notifications only in case of events connected to Authority (a new message in the Thread of particular Request is being considered as such event, thus the messages aren't being duplicated).