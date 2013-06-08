// Load List of Authorities on clickon the tree node.
$('#auth_tree').bind(
    'tree.click',
    function(event) {
        var node = event.node;
        $('#authority_list').html('&nbsp;').load('/instytucje/list/' + String(node.id));
    }
);

// Load List of Authorities on init the tree.
$('#auth_tree').bind(
    'tree.init',
    function(event) {
        $('#authority_list').html('&nbsp;').load('/instytucje/list/');
    }
);

// Show spinner while loading.
$(document).ajaxStart(
    function() {
        $('#spinner').show();
    }
).ajaxStop(
    function() {
        $('#spinner').hide();
    }
);
