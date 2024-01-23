# define some classes to persist data 

class Doc(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    create_date = db.Column(db.DateTime, unique=False, nullable=False)
    vendor = db.Column(db.String(80), unique=True, nullable=False)
    filename = db.Column(db.String(80), unique=True, nullable=False)
    doc_link = db.Column(db.String(80), unique=True, nullable=False) # pointer to file 
    doc_table_id = db.Column(db.Integer, unique=True, nullable=False) # id for query of doc_table schema
    doc_text_id = db.Column(db.Integer, unique=True, nullable=False) # id for query of doc_text schema 

class DocTable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doc_table_id = db.Column(db.Integer, unique=True, nullable=False) # id for query of doc_table schema
    doc_table_data = db.Column(db.PickleType())

class DocText(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doc_text_id = db.Column(db.Integer, unique=True, nullable=False) # id for query of doc_table schema
    doc_text_data = db.Column(db.PickleType())
    

