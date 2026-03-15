import json
from pathlib import Path

root = Path(__file__).resolve().parent
checks = [
    ('pages.json','seo_title',70),('pages.json','seo_description',160),('pages.json','title',120),('pages.json','subtitle',240),
    ('categories.json','seo_title',70),('categories.json','seo_description',160),('categories.json','category_name',60),
    ('products.json','seo_title',70),('products.json','seo_description',160),('products.json','product_name',100),('products.json','short_description',200),('products.json','model_number',50),
    ('applications.json','seo_title',70),('applications.json','seo_description',160),('applications.json','application_name',100),('applications.json','industry',60),
    ('certifications.json','cert_name',100),('certifications.json','issuer',120),('certifications.json','cert_number',80),
    ('capabilities.json','capability_name',100),('capabilities.json','slug',100),('capabilities.json','short_description',200),('capabilities.json','category_tag',60),
    ('comparison-topics.json','topic_title',120),('comparison-topics.json','seo_title',70),('comparison-topics.json','seo_description',160),('comparison-topics.json','summary',500),
    ('faq-items.json','question',300),
]
for file_name, field, limit in checks:
    data = json.loads((root / file_name).read_text())
    if isinstance(data, dict):
        continue
    for item in data:
        value = item.get(field)
        if value is not None and len(value) > limit:
            key = item.get('slug') or item.get('model_number') or item.get('question') or item.get('title')
            print(f'{file_name}: {field} too long ({len(value)}>{limit}) :: {key}')
