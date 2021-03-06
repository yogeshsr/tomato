import logging
from datawinners.main.couchdb.utils import all_db_names
from datawinners.main.database import get_db_manager
from datawinners.project.models import Project
from mangrove.errors.MangroveException import DataObjectAlreadyExists
from migration.couch.utils import migrate, mark_as_completed
from mangrove.datastore.documents import FormModelDocument, SurveyResponseDocument
from mangrove.transport.contract.survey_response import SurveyResponse
from mangrove.form_model.form_model import FormModel


list_all_projects = """
function(doc) {
    if (doc.document_type == 'Project') {
            emit(doc._id, null);
    }
}
"""
list_all_form_models = """
function(doc) {
    if (doc.document_type == 'FormModel') {
            emit(doc._id, null);
    }
}
"""


def remove_state_from_project(dbm):
    for row in dbm.database.query(list_all_projects, include_docs=True):
        try:
            document_data = row.doc
            document_data.pop('state')
            dbm._save_document(Project.wrap(document_data), process_post_update=False)
        except Exception as e:
            logging.error('Removing state in project failed for database : %s, doc with id: %s', dbm.database_name, row.id)
            logging.error(e)


def remove_state_from_form_model(dbm):
    for row in dbm.database.query(list_all_form_models, include_docs=True):
        try:
            document_data = row.doc
            document_data.pop('state')
            form_model = FormModel.new_from_doc(dbm, (FormModelDocument.wrap(document_data)))
            form_model.save()
        except DataObjectAlreadyExists as d:
            form_model.create_snapshot()
            json_snapshots = {}
            for key, value in form_model._snapshots.items():
                json_snapshots[key] = [each._to_json() for each in value]
            form_model._doc.snapshots = json_snapshots
            dbm._save_document(form_model._doc, process_post_update=False)
        except Exception as e:
            logging.error('Removing state in form model failed for database : %s, doc with id: %s', dbm.database_name, row.id)
            logging.error(e)


def remove_state_from_survey_response(dbm):
    rows = dbm.database.iterview("surveyresponse/surveyresponse", 1000, reduce=False, include_docs=True)
    for row in rows:
        try:
            document_data = row.doc
            document_data.pop('test')
            SurveyResponse.new_from_doc(dbm, SurveyResponseDocument.wrap(document_data)).save()
        except Exception as e:
            logging.error('Removing state in survey response failed for database : %s, doc with id: %s', dbm.database_name,
                          row.id)
            logging.error(e)


def migrate_project_to_remove_state(db_name):
    logger = logging.getLogger(db_name)
    try:
        logger.info('Starting migration')
        dbm = get_db_manager(db_name)
        remove_state_from_project(dbm)
        remove_state_from_form_model(dbm)
        remove_state_from_survey_response(dbm)
        mark_as_completed(db_name)
    except Exception as e:
        logger.exception(e.message)


migrate(all_db_names(), migrate_project_to_remove_state, version=(11, 0, 2))