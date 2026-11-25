"""A MOCK national ID register, standing in for NIRA (the National Identification and
Registration Authority) in this prototype.

The real system would query NIRA's verification service. Here a small table of
fictitious people lets the identity step work end to end without any real data.
The result advises the LC I chairperson; the LC I still confirms in person.
"""

# Fictitious NIN -> name on the mock ID. Every entry is invented sample data.
MOCK_REGISTER = {
    "CF85001234ABCD": "Grace Nakato",
    "CM92004567EFGH": "Isaac Mugisha",
    "CF70007890IJKL": "Florence Atim",
    "CM88001122MNOP": "John Ssemwogerere",
    "CF95003344QRST": "Harriet Nansubuga",
    "CM79005566UVWX": "Robert Okot",
    "CF83007788YZAB": "Betty Namuddu",
    "CM90009900CDEF": "Paul Kizza",
    "CF76001357GHIJ": "Annet Nakiyimba",
    "CM86002468KLMN": "Moses Waiswa",
    "CF91003579OPQR": "Sylvia Nambi",
    "CM84004680STUV": "Ronald Lubega",
    "CF80005791WXYZ": "Joyce Nalwoga",
    "CM93006802ABCE": "Henry Mubiru",
    "CF89004713DEFG": "Christine Namale",
    "CM87005824HIJK": "Patrick Wasswa",
    "CF88007531KYEA": "Sarah Nalubega",
    "CM91008642KYEB": "Daniel Ssekandi",
    "CF79009753KYEC": "Rose Nakimuli",
    "CM85001864KYED": "Joseph Kawuki",
}

MATCHED, NAME_DIFFERS, NOT_FOUND = "matched", "name_differs", "not_found"


def check_identity(nin, name):
    """Compare a NIN and name with the mock register. Returns (result, message)."""
    registered = MOCK_REGISTER.get((nin or "").upper())
    if registered is None:
        return NOT_FOUND, "This NIN is not in the mock national ID register. Check the ID card before confirming."
    if " ".join(registered.lower().split()) != " ".join((name or "").lower().split()):
        return NAME_DIFFERS, f"The mock national ID register has this NIN under “{registered}”. Check the ID card."
    return MATCHED, "The NIN and name match the mock national ID register."
