var submissionLogController = function($scope, $location, $routeParams, submissionService){
	$scope.submissions = [];
	$scope.init = function(){
		var onSuccess = function(result){
			var s=[];
			var parser = new DOMParser();

			result.rows.forEach(function(submission) {
				var xmldoc  = parser.parseFromString(submission.doc.Response,"text/xml");
				var form_code = xmldoc.firstChild.tagName;
    			if(submission.doc.document_type=='SurveyResponse' && form_code==$routeParams.projectName)
       				s.push(submission.doc.Response);
			});	
			$scope.$apply(function(){
				$scope.submissions = s;
			});
		};
		submissionService.getSubmissions().then(onSuccess);
	};
	$scope.submissionLog = function(project){
		$location.path('/submissionLog/' + project.id)
	};
	$scope.init();
}

dcsApp.controller('submissionLogController',['$scope','$location','$routeParams', 'submissionService',submissionLogController]); 