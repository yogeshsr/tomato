
var listProjectController = function($scope, $location, projectService){
	$scope.projects = [];
	$scope.init = function(){
		var onSuccess = function(result){
			$scope.projects = result.data;
		};

		var onError = function(response){
			console.log(response.status);
		};

		projectService.getProjects().then(onSuccess, onError);
	};	

	$scope.downloadForm = function(project){
		var onSuccess = function(result){
			project = {'details':project,'xform':result.data.transformed_xform}
			projectService.storeproject(project)	
		};

		projectService.getXform(project.id).then(onSuccess);
		getLocalProjects();
	};

	var getLocalProjects = function(){
		var onGetSuccess = function(result){
			var s=[];

			result.rows.forEach(function(project) {
    			if(project.doc.xform!=undefined)
       				s.push(project);
			});	
			$scope.$apply(function(){
				$scope.localProjects = s;
			});
		};
		projectService.getlocalProjects().then(onGetSuccess);
	}

	$scope.submission = function(project){
		$location.path('/submission/' + project.id);
	};

	$scope.submissionLog = function(project){
		$location.path('/submissionLog/' + project.doc.name);
	};
	$scope.init();
	getLocalProjects();
};


dcsApp.controller('listProjectController',['$scope','$location','projectService',listProjectController]); 

