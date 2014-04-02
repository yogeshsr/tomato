var projectService = function($http){
	offlineDB = new PouchDB('dcs');
	var getProjects = function(){
		 return $http.get('http://10.211.55.4:8000/projects_temp/');
	};

	var getXform = function(projectId){
		return $http.get('http://10.211.55.4:8000/questionnaire_temp/'+projectId+'/')
	};

	var getlocalProjects = function(projectId){
		return offlineDB.allDocs({include_docs: true});
	};

	var deleteProject = function(projectId){
		return offlineDB.remove(projectId);
	};

	var storeproject = function(project){
		return offlineDB.put({
			"name":project.details.name,
			"xform":project.xform
		},project.details.id).then(function(response){console.log('Project stored locally')})
	};

	return { 
		getProjects: getProjects,
		getXform: getXform,
		storeproject: storeproject,
		deleteProject:deleteProject,
		getlocalProjects:getlocalProjects
	}
};

dcsApp.factory('projectService',['$http', projectService]);