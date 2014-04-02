var dcsApp = angular.module('dcsApp', ['ngResource', 'ngRoute']);

dcsApp.config(['$routeProvider',function($routeProvider){
	$routeProvider
		.when('/list',{
			controller: 'listProjectController',
			templateUrl:'partials/listProject.html'
		})
		.when('/submission/:projectId',{
			controller:'submissionController',
			templateUrl:'partials/submission.html'
		})
		.when('/submissionLog/:projectName',{
			controller:'submissionLogController',
			templateUrl:'partials/submissionLog.html'
		})
		.otherwise({
			redirectTo: '/list'
		});
}]);
