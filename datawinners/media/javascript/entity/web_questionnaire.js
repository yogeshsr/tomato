$(document).ready(function () {

    $(".location_field").catcomplete({
        source: "/places"
    });

    if ($("#cancel_submission_warning_message").length) {
        DW.bind_project_links = function () {
            return;
        }

        DW.edit_datasender = new DW.data_submission({});
    }

    $('.secondary_tab li:first-child').attr('class', 'inactive');
    $('.secondary_tab li:nth-child(2)').attr('class', 'active');
});