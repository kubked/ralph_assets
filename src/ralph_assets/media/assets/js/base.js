(function(){
    "use strict";

    var Bulk = function () {};

    Bulk.prototype.get_ids = function(){
        var ids = [];
        $("#assets_table input[type=checkbox]").each(
            function(index, val){
                if(val.checked) {
                    ids.push($(val).val());
                };
            }
        );
        return ids;
    }

    Bulk.prototype.edit_selected = function() {
        var ids = this.get_ids();
        if (ids.length) {
            window.location.href = 'bulkedit?select=' + ids.join('&select=');
        }
        return false;
    };

    Bulk.prototype.invoice_report_selected = function() {
        var ids = this.get_ids();
        if (ids.length){
            window.location.href = 'invoice_report?select=' + ids.join('&select=');
        }
    };

    Bulk.prototype.addAttachment = function(type) {
        var ids = this.get_ids();
        if (ids.length){
            window.location.href = 'add_attachment/' + type + '/?select=' + ids.join('&select=');
        }
    };
    Bulk.prototype.invoice_report_search_query = function () {
        var params = window.location.search;
        if (params.length){
            window.location.href = 'invoice_report' + params + '&from_query=1';
        }
    };

    Bulk.prototype.transition_selected = function(type) {
        var ids = this.get_ids();
        if (
            ids.length &&
            $.inArray(type, ['release-asset', 'return-asset', 'loan-asset']) != -1
        ) {
            window.location.href = 'transition?select=' + ids.join('&select=') + '&transition_type=' + type;
        }
    };

    Bulk.prototype.transition_search_query = function(type) {
        var params = window.location.search;
        if (
            params.length &&
            $.inArray(type, ['release-asset', 'return-asset', 'loan-asset']) != -1
        ) {
            window.location.href = 'transition' + params + '&from_query=1&transition_type=' + type;
        }
    };

    $(document).ready(function() {
        var bulk = new Bulk();
        $('#post_edit_all').click(function() {
            bulk.edit_selected();
        });
        $('#post_invoice_report_selected').click(function() {
            bulk.invoice_report_selected();
        });
        $('#post_invoice_report_search_query').click(function() {
            bulk.invoice_report_search_query();
        });

        $(" #post_release_transition_selected, \
            #post_return_transition_selected, \
            #post_loan_transition_selected \
        ").click(function() {
            var type = $(this).data('transition-type');
            bulk.transition_selected(type);
        });

        $(" #post_release_transition_search_query, \
            #post_return_transition_search_query, \
            #post_loan_transition_search_query \
        ").click(function() {
            var type = $(this).data('transition-type');
            bulk.transition_search_query(type);
        });
        $('#post_add_attachment').click(function() {
            bulk.addAttachment('asset');
        });

        $('.delete-attachment').click(function() {
            if (!confirm("Are you sure to delete Attachment(s)?")) {
                return false;
            }
            var delete_type = $(this).attr('data-delete-type');
            var form_id = '#' + $(this).attr('data-form-id');
            $(form_id).find("input[name='delete_type']").val(delete_type);
            $(form_id).submit();
        });

        $('.del-asset-btn').click(function() {
            if (!confirm("Are you sure to delete Asset?")) {
                return false;
            }
        });
        require(['reports'], function(reports) {
            reports.setup({
                trigger: $('.pagination').find('a').last(),
                progressBar: '#async-progress',
                etaEl: '#eta'
            });
        });
    });

})();
