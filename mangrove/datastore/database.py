

from threading import Lock
from couchdb import http

from couchdb.design import ViewDefinition
from couchdb.http import ResourceNotFound
import couchdb.client

import settings
from documents import DocumentBase
from datetime import datetime
from mangrove.utils import dates
from mangrove.utils.types import is_empty, is_sequence
from mangrove.errors.MangroveException import NoDocumentError, DataObjectNotFound, FailedToSaveDataObject


_dbms = {}
_dbms_lock = Lock()


def get_db_manager(server=None, database=None, credentials=settings.COUCHDB_CREDENTIALS):
    global _dbms
    assert _dbms is not None

    # use defaults if not passed
    srv = (server if server is not None else settings.SERVER)
    db = (database if database is not None else settings.DATABASE)

    k = (srv, db)
    # check if already created and in dict
    if k not in _dbms or _dbms[k] is None:
        with _dbms_lock:
            if k not in _dbms or _dbms[k] is None:
                # nope, create it
                _dbms[k] = DatabaseManager(credentials, server, database)

    return _dbms[k]


def remove_db_manager(dbm):
    global _dbms
    assert isinstance(dbm, DatabaseManager)
    assert dbm in _dbms.values()

    with _dbms_lock:
        try:
            del _dbms[(dbm.url, dbm.database_name)]
        except KeyError, ex:
            print ex
            assert False
            pass  # must have been already deleted


def _delete_db_and_remove_db_manager(dbm):
    """This is really only used for testing purposes."""
    remove_db_manager(dbm)
    if dbm.database_name in dbm.server:
        del dbm.server[dbm.database_name]


class DataObject(object):
    """
    Superclass for all objects that are essentially wrappers of DB
    data.

    There isn't much API contract that needs to be implemented by
    subclasses:

    - They must have a class level member called __document_class__
      that points to the python-couchdb document class that they use
      internally.

    - A constructor where only 'dbm' is required (for initial
      construction)

    - _set_document call which is used to initialize with a new
      python-couchdb document

    - a member self._doc which is used to hold the python-couchdb
      document
    """

    __document_class__ = None

    @classmethod
    def new_from_doc(cls, dbm, doc):
        assert isinstance(doc, cls.__document_class__)
        me = cls(dbm)
        me._set_document(doc)
        return me

    @classmethod
    def get(cls, dbm, id, get_or_create=False):
        return dbm.get(id, cls, get_or_create)

    def __init__(self, dbm):
        self._doc = None
        self._dbm = dbm

    def _set_document(self, document):
        assert isinstance(document, self.__document_class__)
        self._doc = document

    def save(self):
        if self._doc is None:
            raise NoDocumentError('No document to save')
        return self._dbm._save_document(self._doc)

    def put_attachment(self, document, file, filename=None):
        if self._doc is not None:
            self._dbm.put_attachment(document, file, attachment_name=filename)

    def get_attachment(self, doc_id, filename=None):
           return self._dbm.get_attachments(doc_id, attachment_name=filename)

    def delete(self):
        if self.id is not None:
            self._dbm.delete(self)

    def void(self, void=True):
        if self._doc is not None:
            self._doc.void = void
            self.save()

    def is_void(self):
        return self._doc.void

    @property
    def id(self):
        return self._doc.id if self._doc is not None else None

    @property
    def created(self):
        return self._doc.created


class View(object):
    def __init__(self, database):
        self.database = database

    def _load_all_rows_in_view(self, **values):
        full_view_name = self.name + '/' + self.name
        print '[DEBUG] loading view: %s' % full_view_name
        start = datetime.now()
        rows = self.database.view(full_view_name, **values).rows
        end = datetime.now()
        delta_t = (end - start)
        print "[DEBUG] --- took %s.%s seconds (%s rows)" %\
              (delta_t.seconds, delta_t.microseconds, len(rows))
        return rows

    def _execute(self, **values):
        return self._load_all_rows_in_view(**values)

    def __getattr__(self, name):
        self.name = name
        return self._execute


class DatabaseManager(object):
    def __init__(self, credentials, server=None, database=None  ):
        """
        Connect to the CouchDB server. If no database name is given,
        use the name provided in the settings
        """

        self.url = (server if server is not None else settings.SERVER)
        self.database_name = database or settings.DATABASE
        self.server = couchdb.client.Server(self.url, session=http.Session(retry_delays=[5, 30]))
        self.server.resource.credentials = credentials
        try:
            self.database = self.server[self.database_name]
        except ResourceNotFound:
            self.database = self.server.create(self.database_name)

        self.view = View(self.database)


    def __unicode__(self):
        return u"Connected on %s - working on %s" % (self.url, self.database_name)

    def __str__(self):
        return unicode(self)

    def __repr__(self):
        return repr(self.database)

    def load_all_rows_in_view(self, view_name, **values):
        full_view_name = view_name + '/' + view_name
        print '[DEBUG] loading view: %s' % full_view_name
        start = datetime.now()
        rows = self.database.view(full_view_name, **values).rows
        end = datetime.now()
        delta_t = (end - start)
        print "[DEBUG] --- took %s.%s seconds (%s rows)" %\
              (delta_t.seconds, delta_t.microseconds, len(rows))
        return rows

    def create_view(self, view_name, map, reduce):
        view_document = view_name # views get their own design doc for the time being
        view = ViewDefinition(view_document, view_name, map, reduce)
        view.sync(self.database)

    def test_views(self):
        self._delete_design_docs()
        self.create_default_views()

    def _get_design_docs(self):
        return [self._load_document(row['id'])
                for row in self.database.view('_all_docs', startkey='_design', endkey='_design0')]

    def _delete_design_docs(self):
        for doc in self._get_design_docs(): del self.database[doc.id]

    def _save_document(self, document, modified=None, process_post_update=True, prev_doc=None):
        u"""'Returns document ID''"""
        # TODO: Throw exception if an error
        result = self._save_documents([document], modified)[0]
        # first item is success/failure
        if not result[0]:
            raise FailedToSaveDataObject(str(result))
        if process_post_update:
            document.post_update(self,prev_doc)
        # second item is doc ID
        return result[1]

    def _save_documents(self, documents, modified=None):
        assert is_sequence(documents)
        assert modified is None or isinstance(modified, datetime)
        for doc in documents:
            assert isinstance(doc, DocumentBase)
            doc.modified = (modified if modified is not None else dates.utcnow())

        # TODO: what should we return here? this is what is available from db.update()...
        # The return value of this method is a list containing a tuple for every
        # element in the `documents` sequence. Each tuple is of the form
        # ``(success, docid, rev_or_exc)``, where ``success`` is a boolean
        # indicating whether the update succeeded, ``docid`` is the ID of the
        # document, and ``rev_or_exc`` is either the new document revision, or
        # an exception instance (e.g. `ResourceConflict`) if the update failed.

        # Fix up rev, 'cause bulk update seems not to do that
        results = self.database.update(documents)
        for x in range(len(results)):
            if results[x][0]:
                documents[x]._data['_rev'] = results[x][2]
        return results

    def put_attachment(self, document, attachment, attachment_name=None):
        if attachment_name is not None:
            return self.database.put_attachment(document, attachment, attachment_name)

    def get_attachments(self, id, attachment_name=None):
        if attachment_name is not None:
            file = self.database.get_attachment(id, attachment_name, 'Not Found')
            if isinstance(file, basestring):
                raise LookupError("Attachment not found")
            return file.read()

    def invalidate(self, uid):
        doc = self._load_document(uid)
        doc.void = True
        self._save_document(doc)

    def _delete_document(self, document):
        self.database.delete(document)

    def _load_document(self, id, document_class=DocumentBase):
        """
        Load a document from the DB into an in memory document object.

        Low level interface does not create wrapping DataObject

        """
        if is_empty(id):
            return None
        else:
            return document_class.load(self.database, id=id)

    def get_many(self, ids, object_class):
        """
        Get many data objects at once.

        Returns a (possibly empty) list of retrieved objects

        """
        assert issubclass(object_class, DataObject)
        assert is_sequence(ids)

        objs = []
        rows = self.database.view('_all_docs', keys=ids, include_docs=True)
        for row in rows:
            if 'error' in row:
                continue
            obj = object_class.new_from_doc(self, object_class.__document_class__.wrap(row.get('doc')))
            objs.append(obj)
        return objs

    def get(self, id, object_class, get_or_create=False):
        """
        Return the object from the database with the given
        id. object_class must be given so we know how to wrap the data
        retrieved from the database. If get_or_create is True and
        there is no object in the database with this id then the
        object will be created.
        """
        assert issubclass(object_class, DataObject)

        many = self.get_many([id], object_class)
        if get_or_create and len(many) == 0:
            # create one 'cause none exists
            doc = object_class.__document_class__(id=id)
            doc.store(self.database)
            many.append(object_class.new_from_doc(self, doc))

        if not len(many):
            raise DataObjectNotFound(dataobject_name=object_class.__name__, param="id", value=id)

        return many[0]

    def delete(self, d_obj):
        """
        Deletes the document associated with the data_obj from the database.

        """
        assert isinstance(d_obj, DataObject)

        if d_obj._doc is None:
            raise NoDocumentError

        id = d_obj._doc.id
        self.database.delete(d_obj._doc)
