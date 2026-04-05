def document_to_dict(document):
    data = document.to_mongo().to_dict()
    data["id"] = str(data.pop("_id"))
    return data


def documents_to_dict(documents):
    return [document_to_dict(item) for item in documents]
