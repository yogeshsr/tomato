function displaySuccessMessage(data) {
    $('.success-message-box').text(data["message"]);
    $('.success-message-box').show();
    $('.success-message-box')[0].scrollIntoView();
}
function QuestionnaireReplyViewModel() {
    var self = this;
    self.availableLanguages = ko.observableArray(languages);
    self.language = ko.observable();
    self.language_display = ko.computed(function() {
        return self.language();
    });

    self.addLanguageText = ko.observable(gettext("Add Language"));

    self.newLanguageName = DW.ko.createValidatableObservable({value: ""});
    var languageNameEmptyMessage = gettext("Please enter a name for your language.");
    self.newLanguageName.subscribe(function () {
            DW.ko.mandatoryValidator(self.newLanguageName, languageNameEmptyMessage);
        }
    );

    self.language.subscribe(function () {
        $.getJSON("/languages/custom_messages", {'language': languageViewModel.language()}).success(function (data) {
            createObservableMessageItemsFor(data, languageViewModel.messages,
                languageViewModel.messagesInitialState);
        });
    }, self, 'change');

    self.sortLanguages = function () {
        self.availableLanguages.sort(function (left, right) {
            return left.name.toLowerCase() == right.name.toLowerCase() ? 0 : (left.name.toLowerCase() < right.name.toLowerCase() ? -1 : 1)
        });
    };

    self.save = function (callback) {
        if (!self.isValid() || !self.isMessageModified()) return;
        DW.loading();
        languageViewModel.saveButtonText(gettext("Saving..."));
        $.post(post_url, {
                'data': JSON.stringify(ko.toJS(languageViewModel)),
                'csrfmiddlewaretoken':$('input[name=csrfmiddlewaretoken]').val()
            },
            function (data) {
                data = JSON.parse(data);
                languageViewModel.saveButtonText(gettext("Save"));
                displaySuccessMessage(data);
                self.messagesInitialState(ko.toJSON(self.messages()));
                if (typeof callback == "function") callback();
            }
        );

    };
    self.addLanguage = function () {
        if (self.newLanguageName() && self.newLanguageName.valid()) {
            self.addLanguageText(gettext("Adding..."));
            DW.loading();
            $('#add_new_language_pop .yes_button').addClass('ui-state-disabled');
            $.post('/languages/create', {"language_name": self.newLanguageName()})
                .done(function (responseString) {
                    var response = $.parseJSON(responseString);
                    if (response.language_code) {
                        self.addLanguageText(gettext("Add Language"));
                        $('#add_new_language_pop .yes_button').removeClass('ui-state-disabled');
                        $('#add_new_language_pop').dialog('close');
                        self.availableLanguages.pop();
                        self.availableLanguages.push({code: response.language_code, name: response.language_name});
                        self.sortLanguages();
                        self.language(response.language_code);
                        $('.success-message-box').text(gettext("Language Added successfully"));
                        $('.success-message-box').show();

                    } else {
                        self.newLanguageName.setError(response.message);
                        self.addLanguageText(gettext("Add Language"));
                        $('#add_new_language_pop .yes_button').removeClass('ui-state-disabled');
                    }
                })
        } else {
            if (!self.newLanguageName())
                self.newLanguageName.setError(languageNameEmptyMessage);
        }
    };

    self.cancelAddLanguage = function () {
        $('#add_new_language_pop').dialog('close');
    }
}

QuestionnaireReplyViewModel.prototype = new ReplyMessageViewModel();
QuestionnaireReplyViewModel.prototype.constructor = QuestionnaireReplyViewModel;
