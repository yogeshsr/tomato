var pouchDAO = function($http, pouchDAO){
	offlineDB = new PouchDB('dcs');

	var getXform = function(projectId){
		return $http.get('http://10.211.55.4:8000/questionnaire_temp/'+projectId+'/')
	};

	var getDocumentOfType = function(documentType){
		return '<root xmlns:xf="http://www.w3.org/2002/xforms" xmlns:h="http://www.w3.org/1999/xhtml" xmlns:ev="http://www.w3.org/2001/xml-events" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:jr="http://openrosa.org/javarosa"><model><instance>         <age_calculation-121 id="age_calculation-121">           <n1/>           <n2/>           <n3/>           <sum/>           <meta>             <instanceID/>           </meta>         <form_code>121</form_code><eid>rep276</eid></age_calculation-121>       </instance></model><form autocomplete="off" novalidate="novalidate" class="or clearfix" id="age_calculation-121"> <!--This form was created by transforming a OpenRosa-flavored (X)Form using an XSLT sheet created by Enketo LLC.--><section class="form-logo"> </section><h3 id="form-title">age_calculation-121</h3>           <label class="question non-select "><span lang="" class="question-label active">number1</span><input autocomplete="off" type="number" name="/age_calculation-121/n1" data-type-xml="int"/></label>     <label class="question non-select "><span lang="" class="question-label active">number1</span><input autocomplete="off" type="number" name="/age_calculation-121/n2" data-type-xml="int"/></label>     <label class="note non-select "><span lang="" class="question-label active">sum:<span class="or-output" data-value=" /age_calculation-121/n3 "></span></span><input autocomplete="off" type="text" name="/age_calculation-121/sum" data-type-xml="string" readonly="readonly"/></label>    <fieldset id="or-calculated-items" style="display:none;"><label class="calculation non-select "><input autocomplete="off" type="hidden" name="/age_calculation-121/n3" data-calculate=" /age_calculation-121/n1 + /age_calculation-121/n2 " data-type-xml="string"/></label><label class="calculation non-select "><input autocomplete="off" type="hidden" name="/age_calculation-121/meta/instanceID" data-calculate="concat(\'uuid:\', uuid())" data-type-xml="string"/></label></fieldset></form></root>';
	};

	var post = function(data){
		return offlineDB.put({
			"xform":project.xform
		},project.details.id).then(function(response){console.log('Project stored locally')})
	};

	return {
		post:post,
		getDocumentOfType:getDocumentOfType
	}
};

dcsApp.factory('pouchDAO',['$http', pouchDAO]);