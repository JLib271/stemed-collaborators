"""The STEMEd+ disciplines, read from the list shared across STEMEd+ Commons
(humeta-profile's stemedplus_disciplines.json, stored here as
stemedplus_disciplines.json; see stemedplus_disciplines.py). STEMEd+ Jobs,
Funding, Digest, Conferences, Collaborators, and Graduate Programs all build
from the same list."""
from . import stemedplus_disciplines as shared

DISCIPLINES = tuple(name for name, _ in shared.rules())
FIELD_DISCIPLINES = shared.field_labels()
