var created_datasender_row_markup = "<tr>\
                    <td>${name}</td>\
                    <td>${id}</td>\
                    <td>${location}</td>\
                    <td>${coordinates}</td>\
                    <td>${mobile_number}</td>\
                    <td>${email}</td>\
                  </tr>";

$.template("created_datasenders", created_datasender_row_markup );

$(document).ready(function () {
    $("#popup-import").dialog({
        autoOpen: false,
        modal: true,
        title: gettext("Import a Data Senders list"),
        zIndex: 200,
        width: 940,
        close: function () {
            if ($('#message').length) {
                window.location.replace(document.location.href);
            }
        }
    });

    $("#import-datasenders").bind("click", function () {
        $("#popup-import").dialog("open");
        $('#message').remove();
        $('#error_body').html('');
        $("#error_import_section").hide();
        $("#success_import_section").hide();
        $('#success_body').html("");
    });

    $(".close_import_dialog").bind("click", function () {
        $("#popup-import").dialog("close");
    });

    function refresh_error_table(responseJSON) {
        $('#error_tbody').html('');
        if (responseJSON.failure_imports.length > 0) {
            $("#error_table_message").html(gettext(responseJSON.failure_imports.length + " records failed to import"));
            $("#error_import_section").show();
        }
        $.each(responseJSON.failure_imports, function (index, element) {
            $("#error_import_section table tbody").append("<tr><td>" + element.row_num + "</td><td>" + JSON.stringify(element.row) + "</td><td>"
                + element.error + "</td></tr>");
        });
    };

    function refresh_success_table(responseJSON) {
        if (responseJSON.successful_imports.length <= 0) {
            $("#success_import_section").hide();
        }
        else {
            $("#success_table_message").html(gettext(responseJSON.successful_imports.length + " records successfully imported"));
            $("#success_import_section").show();
        }
        $("#success_body").html('');
        _.each(responseJSON.successful_imports, function (datasenderjson) {
            $("#success_body").append($.tmpl("created_datasenders", datasenderjson));
        });
    };

    var uploader = new qq.FileUploader({
        // pass the dom node (ex. $(selector)[0] for jQuery users)
        element: document.getElementById('file_uploader'),
        // path to server-side upload script
        action: import_datasenders_link,
        params: {},
        onSubmit: function () {
            $.blockUI({ message: '<h1><img src="/media/images/ajax-loader.gif"/><span class="loading">' + gettext("Just a moment") + '...</span></h1>', css: { width: '275px'}});
        },
        onComplete: function (id, fileName, responseJSON) {
            $.unblockUI();
            $('#message').remove();
            $('#error_body').html('');
            $("#error_import_section").hide();
            if ($.isEmptyObject(responseJSON)) {
                $('<div id="message" class="error_message message-box clear-left">' + gettext("Sorry, an error occured - the reason could be connectivity issues or the import taking too long to process.  Please try again.  Limit the number of subjects you import to 200 or less.") + '</div>').insertAfter($('#file-uploader'));
            }
            else {
                refresh_success_table(responseJSON);
                if (responseJSON.success == true) {
                    $('<div id="message" class="success_message success-message-box">' + responseJSON.message + '</div>').insertAfter($('#file-uploader'));
                }
                else {

                    if (responseJSON.error_message) {
                        $('<div id="message" class="error_message message-box clear-left">' + responseJSON.error_message + '</div>').insertAfter($('#file-uploader'));
                    }
                    else {
                        $('<div id="message" class="error_message message-box clear-left">' + responseJSON.message + '</div>').insertAfter($('#file-uploader'));
                    }
                    refresh_error_table(responseJSON);
                }
            }
        }
    });
});

