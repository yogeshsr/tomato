var submissionService = function($http){
	offlineDB = new PouchDB('dcs');

	var getSubmissions = function(projectId){
		return offlineDB.allDocs({include_docs: true});
	};

	return { 
		getSubmissions: getSubmissions,
	}
};

dcsApp.factory('submissionService',['$http',submissionService]);