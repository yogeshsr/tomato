DW.get_trial_number_info = function(){
    $.post(window.location.href,{country:$('#id_country').val()},
            function(response){
                console.log(response);
            }
    );
};

$(document).ready(function(){
   $('#id_country').change(DW.get_trial_number_info)
});