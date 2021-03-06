describe('datasender actions', function () {
    var tableSpy;
    beforeEach(function () {
        tableSpy = jasmine.createSpy('table');
    });

    describe('datasender action delete', function () {

        it('should call warning popup on deleting superusers', function () {
            var superusers_selected = spyOn(window, "get_user_names_from_selected_datasenders");
            superusers_selected.andReturn(['admin']);
            var warning_dialog_spy = spyOn(window, "delete_all_ds_are_users_show_warning");

            handle_datasender_delete(tableSpy, ['admin'], true);

            var args = "<li>admin</li>";
            expect(warning_dialog_spy).toHaveBeenCalledWith(args);
        });

        it('should show warning box when deleting combination of users and datasenders', function () {
            setFixtures('<div id="note_for_delete_users"><ul class="users_list"></ul></div>');

            var superusers_selected = spyOn(window, "get_user_names_from_selected_datasenders");
            superusers_selected.andReturn(['admin']);
            var warning_dialog_spy = spyOn(window, "warnThenDeleteDialogBox");
            var selected_ds = ['admin', 'rep1'];

            handle_datasender_delete(tableSpy, selected_ds, false);

            expect($('#note_for_delete_users')).not.toBeHidden();
            expect(warning_dialog_spy).toHaveBeenCalledWith(selected_ds, false, 'reporter', window);
        });

        it('should populate warning box with user list when deleting combination of users and datasenders', function () {
            setFixtures('<div id="note_for_delete_users"><ul class="users_list"></ul></div>');

            var superusers_selected = spyOn(window, "get_user_names_from_selected_datasenders");
            superusers_selected.andReturn(['admin']);
            var warning_dialog_spy = spyOn(window, "warnThenDeleteDialogBox");

            handle_datasender_delete(tableSpy, ['admin', 'rep1'], false);

            var args = "<li>admin</li>";
            var warnMsg = $('#note_for_delete_users .users_list');
            expect(warnMsg).toHaveHtml(args);
        });

        it('should show warning box when deleting only datasenders', function () {
            setFixtures('<div id="note_for_delete_users"><ul class="users_list"></ul></div>');

            var superusers_selected = spyOn(window, "get_user_names_from_selected_datasenders");
            superusers_selected.andReturn([]);
            var warning_dialog_spy = spyOn(window, "warnThenDeleteDialogBox");
            var selected_ds = ['rep2', 'rep1'];

            handle_datasender_delete(tableSpy, selected_ds, false);

            expect($('#note_for_delete_users')).toBeHidden();
            expect(warning_dialog_spy).toHaveBeenCalledWith(selected_ds, false, 'reporter', window);
        });

        it('should call superusers from server if select all(all) is selected', function () {
            user_dict = [
                {'name': 'id'}
            ];
            var getUsers = spyOn(window, 'usersInSearchedDS');
            get_user_names_from_selected_datasenders(tableSpy, ['rep1'], true);
            expect(getUsers).toHaveBeenCalled();
        });

        it('should get users from selected datasenders', function () {
            user_dict = {'id1': 'user1', 'id2': 'user2'};
            var getUsers = spyOn(window, 'usersInSearchedDS');
            setFixtures('<table id="test_table"><tbody><tr><td><input type="checkbox" class="row_checkbox" value="id1" checked></td></tr>' +
                '<tr><td><input type="checkbox" class="row_checkbox" value="id2" checked></td></tr>' +
                '<tr><td><input type="checkbox" class="row_checkbox" value="rep1" checked></td></tr>' +
                '<tr><td><input type="checkbox" class="row_checkbox" value="rep2" checked></td></tr>' +
                '</tbody></table>');

            var result = get_user_names_from_selected_datasenders('#test_table', ['rep1'], false);

            expect(result).toEqual(['user1', 'user2']);
        });

        it('should reset to first page upon deleting all datasenders', function () {
            var table = jasmine.createSpyObj('table', ['fnSettings']);

            var pageIndex = get_updated_table_page_index(table, ['rep1'], true);

            expect(pageIndex).toEqual(0);
        });

        it('should remain in same page upon deleting all datasenders in any page except last page', function () {
            var fnSettingsMock = jasmine.createSpy("settings").andReturn({
                'fnDisplayEnd': function () {
                    return 1;
                },
                'fnRecordsDisplay': function () {
                    return 2;
                },
                '_iDisplayStart': 2
            });
            tableSpy = {
                "fnSettings": fnSettingsMock
            };

            var pageIndex = get_updated_table_page_index(tableSpy, ['rep1'], false);

            expect(pageIndex).toEqual(2);
        });

        it('should reset to first page upon deleting all datasenders in last page', function () {
            var fnSettingsMock = jasmine.createSpy("settings").andReturn({
                'fnDisplayEnd': function () {
                    return 1;
                },
                'fnRecordsDisplay': function () {
                    return 1;
                },
                '_iDisplayStart': 2
            });
            tableSpy = {
                "find": function (parms) {
                    return {"length": 1};
                },
                "fnSettings": fnSettingsMock
            };

            var pageIndex = get_updated_table_page_index(tableSpy, ['rep1'], false);

            expect(pageIndex).toEqual(0);
        });
    });

    describe("datasender action edit", function () {

        it("should fire ajax edit with right parameters", function () {
            var jquery_ajax = spyOn($, "ajax");

            handle_datasender_edit(tableSpy, ['REp1']);

            expect($.ajax.mostRecentCall.args[0]['url']).toEqual('/entity/datasender/edit/rep1/');
        });

        it("should populate edit dialog when edit successful", function () {
            jasmine.getFixtures().set('<div id=datasender-popup></div>');
            var jquery_ajax = spyOn($, "ajax").andCallFake(function (e) {
                e.success('<div>Edit successful</div>');
            });
            var editActionInitializer = spyOn(DW, 'InitializeEditDataSender').andCallFake(function () {
                return {init: jasmine.createSpy('init')};
            });

            handle_datasender_edit(tableSpy, ['REp1']);

            expect($("#datasender-popup")).toHaveHtml('<div>Edit successful</div>');
        });

        it("should initialize edit action when edit successful", function () {
            jasmine.getFixtures().set('<div id=datasender-popup></div>');
            var jquery_ajax = spyOn($, "ajax").andCallFake(function (e) {
                e.success('<div>Edit successful</div>');
            });
            var initSpy = jasmine.createSpy('init');
            var editActionInitializer = spyOn(DW, 'InitializeEditDataSender').andCallFake(function () {
                return {init: initSpy };
            });

            handle_datasender_edit(tableSpy, ['REp1']);

            expect(initSpy).toHaveBeenCalled();
        });

        it("should initialize and open dialog when edit successful", function () {
            jasmine.getFixtures().set('<div id=datasender-popup></div>');
            var jquery_ajax = spyOn($, "ajax").andCallFake(function (e) {
                e.success('<div>Edit successful</div>');
            });
            var initSpy = jasmine.createSpy('init');
            var editActionInitializer = spyOn(DW, 'InitializeEditDataSender').andCallFake(function(){
                return {init: initSpy };
            });
            var anotherDialogSpy = jasmine.createSpy("dialog");
            var mockDialog = spyOn($.fn, "dialog").andReturn({
                "dialog": anotherDialogSpy
            });
            spyOn(window, "gettext").andReturn("someText");

            handle_datasender_edit(tableSpy, ['REp1']);

            expect(mockDialog).toHaveBeenCalledWith('option','title', "someText");
            expect(anotherDialogSpy).toHaveBeenCalledWith("open")
        });

    });
});