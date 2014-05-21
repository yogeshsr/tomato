var update_table = function (xls) {
    xls_dict = xls;
    var grid;
    var data = [];
    var columns = [];
    var sheets = {'survey': '#survey', 'choices': '#choices', 'cascades': '#cascades', 'other': '#other'};

    var options = {
        editable: true,
        enableAddRow: true,
        enableCellNavigation: true,
        asyncEditorLoading: false,
        autoEdit: false
    };

for (var i = 0; i < 26; i++) {
    columns.push({
        id: i,
        name: String.fromCharCode("A".charCodeAt(0) + i),
        field: i,
        width: 200,
        editor: Slick.Editors.Text
    });
}

    var index = 0;

    for (var sheet in xls_dict) {
        for (var row in xls_dict[sheet]) {
            var d = (data[index++] = {})
            for (var value in xls_dict[sheet][row]) {
                d[value] = xls_dict[sheet][row][value]
            }
        }

        grid = new Slick.Grid(sheets[sheet], data, columns, options);

        grid.onAddNewRow.subscribe(function (e, args) {
            var item = args.item;
            grid.invalidateRow(data.length);
            data.push(item);
            grid.updateRowCount();
            grid.render();
        });
        index = 0;
        data = [];
        document.getElementById(sheet).innerHTML = '<div>' + sheet + '</div>' + document.getElementById(sheet).innerHTML;
    }
}