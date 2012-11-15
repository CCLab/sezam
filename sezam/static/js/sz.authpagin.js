$('#authority_pagination').find('a').click(
    function(event) {
        var $this = $(this);
        var url = $this.attr('href');
        // alert(url);
        $('#authority_list').html('&nbsp;').load('/authority/list/' + url);
        return false;
    }
);
