requirejs.config( {
    baseUrl: "/media/enketo-core/lib",
    paths: {
        "enketo-js": "../src/js",
        "enketo-widget": "../src/widget",
        "enketo-config": "../config.json",
        "text": "text/text",
        "xpath": "xpath/build/xpathjs_javarosa",
        "file-manager": "file-manager/src/file-manager",
        "jquery.xpath": "jquery-xpath/jquery.xpath",
        "jquery.touchswipe": "jquery-touchswipe/jquery.touchSwipe"
    },
    shim: {
        "xpath": {
            exports: "XPathJS"
        },
        "bootstrap": {
            deps: [ "jquery" ],
            exports: "jQuery.fn.popover"
        },
        "widget/date/bootstrap3-datepicker/js/bootstrap-datepicker": {
            deps: [ "jquery" ],
            exports: "jQuery.fn.datepicker"
        },
        "widget/time/bootstrap3-timepicker/js/bootstrap-timepicker": {
            deps: [ "jquery" ],
            exports: "jQuery.fn.timepicker"
        },
        "Modernizr": {
            exports: "Modernizr"
        }
    }
} );

requirejs( [ 'jquery', 'Modernizr', 'enketo-js/Form' ],
    function( $, Modernizr, Form ) {
        var loadErrors, form;

        //if querystring touch=true is added, override Modernizr
        if ( getURLParameter( 'touch' ) === 'true' ) {
            Modernizr.touch = true;
            $( 'html' ).addClass( 'touch' );
        }

        //check if HTML form is hardcoded or needs to be retrieved
        $( '.guidance' ).remove();
        var $data;
        data = xform_xml.replace( /jr\:template=/gi, 'template=' );
        $data = $( $.parseXML( data ) );
        formStr = ( new XMLSerializer() ).serializeToString( $data.find( 'form:eq(0)' )[ 0 ] );
        modelStr = ( new XMLSerializer() ).serializeToString( $data.find( 'model:eq(0)' )[ 0 ] );

        $( '#validate-form' ).before( formStr );
        initializeForm();

        //validate handler for validate button
        $( '#validate-form' ).on( 'click', function() {
            form.validate();
            if ( !form.isValid() ) {
                alert( 'Form contain errors. Please see fields marked in red.' );
            } else {
                DW.blockUI({ message: '<h1><img src="/media/images/ajax-loader.gif"/><span class="loading">' + gettext("Just a moment") + '...</span></h1>', css: { width: '275px'}});
                var data = form.getDataStr();
                var saveURL= submissionUpdateUrl || submissionCreateUrl;

                var success = function(data,status){
                    DW.unblockUI();
                    window.location.replace(surveyResponseId == '' ? submissionURL : submissionLogURL);
                };
                var error = function(status){
                    alert('Unable to submit form, please try after some time');
                    DW.unblockUI();
                };

                $.post(saveURL,{'a':data}).done(success).fail(error);
            }
        } );

        //initialize the form

        function initializeForm() {
            form = new Form( 'form.or:eq(0)', modelStr, dataStrToEdit );
            //for debugging
            window.form = form;
            //initialize form and check for load errors
            loadErrors = form.init();
            if ( loadErrors.length > 0 ) {
                alert( 'loadErrors: ' + loadErrors.join( ', ' ) );
            }
        }

        //get query string parameter

        function getURLParameter( name ) {
            return decodeURI(
                ( RegExp( name + '=' + '(.+?)(&|$)' ).exec( location.search ) || [ , null ] )[ 1 ]
            );
        }
    } );
