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

    // Multi-file attachments.
    $('#attach-files').MultiFile({ 
        list: '#attach-list',
        max: 5,
        STRING:{
            file: '<em title="Kliknij, aby usunąć" onclick="$(this).parent().prev().click()">$file</em>',
            remove: '<i class="icon-remove-sign"></i>',
            selected: 'Selecionado: $file',
            denied: 'Nie możesz wybrać plik typu $ext.\nSpróbuj ponownie...',
            duplicate: 'Ten plik został już wybrany:\n$file!'
        }
    });
  });