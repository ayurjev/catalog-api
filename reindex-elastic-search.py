


from models import mongo_client, es_client


catalog_items = mongo_client.db.items
for item in catalog_items.find({}, {"_id": True, "title": True}):
    print(item.get("_id"), item.get("title"))
    es_client.index(index="items", doc_type="item", id=item.get("_id"), body={"title": item.get("title")})
print("done!")