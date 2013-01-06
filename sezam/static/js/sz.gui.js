$(function() {
  
    // Authority tree initialization.
    $('#auth_tree').tree({
        autoOpen: 0,
        autoEscape: false,
        selectable: true
    });

    // Message draft auto-preview.
    $('#id_body').on(
        'keyup',
        function(event) {
            $('#request_body_preview').html($(event.target).val().replace(/\n/g, "<br//>"));
            }
        );
  
    // Message draft subject auto-preview.
    $('#id_subject').on(
        'keyup',
        function(event) {
            $('#request_subject_preview').html($(event.target).val().replace(/\n/g, "<br//>"));
            }
        );

    // "Date after" filter datepicker.
    $('#date_after').datepicker({format: 'dd-mm-yyyy'}).on(
        'changeDate',
        function(event){
            $('#date_after').datepicker('hide');
            }
        );
    
    // "Date before" filter datepicker.
    $('#date_before').datepicker({format: 'dd-mm-yyyy'}).on(
        'changeDate',
        function(ev){
            $('#date_before').datepicker('hide');
            }
        );
  });