# Released under the MIT License. See LICENSE for details.
#PCModder was here
#All rights to PCModder/Mikahael as the Liecense states.
"""Provides party related UI."""

from __future__ import annotations

import math
import weakref
from typing import TYPE_CHECKING, cast#Avarohana was here

import _ba
import ba
from bastd.ui import popup#My last Stand for BS

if TYPE_CHECKING:
    from typing import List, Sequence, Optional, Dict, Any


class PartyWindow(ba.Window):
    """Party list/chat window."""

    def __del__(self) -> None:
        _ba.set_party_window_open(False)

    def __init__(self, origin: Sequence[float] = (0, 0)):
        _ba.set_party_window_open(True)
        self._r = 'partyWindow'
        self._popup_type: Optional[str] = None
        self._popup_party_member_client_id: Optional[int] = None
        self._popup_party_member_is_host: Optional[bool] = None
        self._width = 500
        uiscale = ba.app.ui.uiscale
        self._height = (365 if uiscale is ba.UIScale.SMALL else
                        480 if uiscale is ba.UIScale.MEDIUM else 600)
        super().__init__(root_widget=ba.containerwidget(
            size=(self._width, self._height),
            transition='in_scale',
            color=(0.40, 0.55, 0.20),
            parent=_ba.get_special_widget('overlay_stack'),
            on_outside_click_call=self.close_with_sound,
            scale_origin_stack_offset=origin,
            scale=(2.0 if uiscale is ba.UIScale.SMALL else
                   1.35 if uiscale is ba.UIScale.MEDIUM else 1.0),
            stack_offset=(0, -10) if uiscale is ba.UIScale.SMALL else (
                240, 0) if uiscale is ba.UIScale.MEDIUM else (330, 20)))

        self._cancel_button = ba.buttonwidget(parent=self._root_widget,
                                              scale=0.7,
                                              position=(30, self._height - 47),
                                              size=(50, 50),
                                              label='',
                                              on_activate_call=self.close,
                                              autoselect=True,
                                              color=(0.45, 0.63, 0.15),
                                              icon=ba.gettexture('crossOut'),
                                              iconscale=1.2)
        ba.containerwidget(edit=self._root_widget,
                           cancel_button=self._cancel_button)

        self._menu_button = ba.buttonwidget(
            parent=self._root_widget,
            scale=0.7,
            position=(self._width - 60, self._height - 47),
            size=(50, 50),
            label='...',
            autoselect=True,
            button_type='square',
            on_activate_call=ba.WeakCall(self._on_menu_button_press),
            color=(0.55, 0.73, 0.25),
            iconscale=1.2)
            
        self._test_button = ba.buttonwidget(
            parent=self._root_widget,
            scale=0.7,
            position=(self._width - 120, self._height - 47),
            size=(50, 50),
            label='?',
            autoselect=True,
            button_type='square',
            on_activate_call=ba.WeakCall(self._on_test_button_press),
            color=(0.55, 0.73, 0.25),
            iconscale=1.2)

        info = _ba.get_connection_to_host_info()
        if info.get('name', '') != '':
            title = ba.Lstr(value=info['name'])
        else:
            title = ba.Lstr(resource=self._r + '.titleText')

        self._title_text = ba.textwidget(parent=self._root_widget,
                                         scale=0.9,
                                         color=(0.5, 0.7, 0.5),
                                         text=title,
                                         size=(0, 0),
                                         position=(self._width * 0.5,
                                                   self._height - 29),
                                         maxwidth=self._width * 0.7,
                                         h_align='center',
                                         v_align='center')

        self._empty_str = ba.textwidget(parent=self._root_widget,
                                        scale=0.75,
                                        size=(0, 0),
                                        position=(self._width * 0.5,
                                                  self._height - 65),
                                        maxwidth=self._width * 0.85,
                                        h_align='center',
                                        v_align='center')

        self._scroll_width = self._width - 50
        self._scrollwidget = ba.scrollwidget(parent=self._root_widget,
                                             size=(self._scroll_width,
                                                   self._height - 200),
                                             position=(30, 80),
                                             color=(0.4, 0.6, 0.3))
        self._columnwidget = ba.columnwidget(parent=self._scrollwidget,
                                             border=2,
                                             margin=0)
        ba.widget(edit=self._menu_button, down_widget=self._columnwidget)
        ba.widget(edit=self._test_button, down_widget=self._columnwidget)

        self._muted_text = ba.textwidget(
            parent=self._root_widget,
            position=(self._width * 0.5, self._height * 0.5),
            size=(0, 0),
            h_align='center',
            v_align='center',
            text=ba.Lstr(resource='chatMutedText'))
        self._chat_texts: List[ba.Widget] = []

        # add all existing messages if chat is not muted
        if not ba.app.config.resolve('Chat Muted'):
            msgs = _ba.get_chat_messages()
            for msg in msgs:
                self._add_msg(msg)

        self._text_field = txt = ba.textwidget(
            parent=self._root_widget,
            editable=True,
            size=(530, 40),
            position=(44, 39),
            text='',
            maxwidth=494,
            shadow=0.3,
            flatness=1.0,
            description=ba.Lstr(resource=self._r + '.chatMessageText'),
            autoselect=True,
            v_align='center',
            corner_scale=0.7)

        ba.widget(edit=self._scrollwidget,
                  autoselect=True,
                  left_widget=self._cancel_button,
                  up_widget=self._cancel_button,
                  down_widget=self._text_field)
        ba.widget(edit=self._columnwidget,
                  autoselect=True,
                  up_widget=self._cancel_button,
                  down_widget=self._text_field)
        ba.containerwidget(edit=self._root_widget, selected_child=txt)
        btn = ba.buttonwidget(parent=self._root_widget,
                              size=(50, 35),
                              label=ba.Lstr(resource=self._r + '.sendText'),
                              button_type='square',
                              autoselect=True,
                              position=(self._width - 70, 35),
                              on_activate_call=self._send_chat_message)
        ba.textwidget(edit=txt, on_return_press_call=btn.activate)
        self._name_widgets: List[ba.Widget] = []
        self._roster: Optional[List[Dict[str, Any]]] = None
        self._update_timer = ba.Timer(1.0,
                                      ba.WeakCall(self._update),
                                      repeat=True,
                                      timetype=ba.TimeType.REAL)
        self._update()

    def on_chat_message(self, msg: str) -> None:
        """Called when a new chat message comes through."""
        if not ba.app.config.resolve('Chat Muted'):
            self._add_msg(msg)

    def _add_msg(self, msg: str) -> None:
        import random
        k=((0+random.random()*5.0),(0+random.random()*5.0),(0+random.random()*5.0))  
        txt = ba.textwidget(parent=self._columnwidget,
                            text=msg,
                            h_align='left',
                            v_align='center',
                            size=(0, 13),
                            color=k,
                            scale=0.55,
                            maxwidth=self._scroll_width * 0.94,
                            shadow=0.3,
                            flatness=1.0)
        self._chat_texts.append(txt)
        if len(self._chat_texts) > 40:
            first = self._chat_texts.pop(0)
            first.delete()
        ba.containerwidget(edit=self._columnwidget, visible_child=txt)

    def _on_menu_button_press(self) -> None:
        is_muted = ba.app.config.resolve('Chat Muted')
        uiscale = ba.app.ui.uiscale
        popup.PopupMenuWindow(
            position=self._menu_button.get_screen_space_center(),
            scale=(2.3 if uiscale is ba.UIScale.SMALL else
                   1.65 if uiscale is ba.UIScale.MEDIUM else 1.23),
            choices=['unmute' if is_muted else 'mute'],
            choices_display=[
                ba.Lstr(
                    resource='chatUnMuteText' if is_muted else 'chatMuteText')
            ],
            current_choice='unmute' if is_muted else 'mute',
            delegate=self)
        self._popup_type = 'menu'
        
    def _on_test_button_press(self) -> None:
        is_muted = ba.app.config.resolve('Chat Muted')
        uiscale = ba.app.ui.uiscale
        popup.PopupMenuWindow(
            position=self._test_button.get_screen_space_center(),
            scale=(2.3 if uiscale is ba.UIScale.SMALL else
                   1.65 if uiscale is ba.UIScale.MEDIUM else 1.23),
            choices=['PCModder', "Motion", "End", "Heal", "Punch", "Shield", "Hug", "Floater ON", "Floater OFF", "Whitelist ON", "Whitelist OFF", "Pwp ON", "Pwp OFF", "Powerups ON", "Powerups OFF",
                     'PowerupNameON', 'PowerupNameOFF', 'DiscoLightON', 'DiscoLight OFF', 'PowerupShieldON','PowerupShieldOFF','BombModelON','BombModelOFF','BombNameON', 'BombNameOFF', 'Tag ON', 'Tag OFF',
                     'Animate ON', 'Animate OFF', 'Hp ON', 'Hp OFF', 'TeamMode', 'FFAMode', 'Quit', 'Explo ON','Explo OFF','PopText ON','PopText OFF','Wizard ON','Wizard OFF','Pixie ON','Pixie OFF','Ninja ON','Ninja OFF',
                     'Frosty ON','Frosty OFF', 'Pengu OFF', 'Pengu ON', 'Ali ON', 'Ali OFF', 'Robot ON', 'Robot OFF', 'Santa ON', 'Santa OFF', 'Impact ON', 'Impact OFF', 'Ice ON', 'Ice OFF', 'Sticky ON', 'Sticky OFF',
                     'Spike ON', 'Spike OFF', 'Shock ON', 'Shock OFF', 'Glue ON', 'Glue OFF', 'Knock ON', 'Knock OFF', 'PWPIce ON', 'PWPIce OFF', 'PWPSplint ON', 'PWPSplint OFF', 'PWPSlime ON', 'PWPSlime OFF', 'PWPSweat ON', 'PWPSweat OFF',
                     'SlimeSnow','SplinterSnow','IceSnow','SparkSnow','SweatSnow','NormalShower','StickyShower','IceShower','GlueShower', 'CursyShower', 'ImpactShower', 'FrozenShower', 'PwpShower', 'MAP_TEX', 'Pink', 'Snow', 'Snow2', 'Blue', 'Red'
                     'Red2', 'Red3', 'Red4', 'Orange', 'Orange2', 'Yellow', 'Dirt', 'Dirt2', 'Dark', 'Smooth', 'Smooth2', 'Colorful'],
            choices_display=[ba.Lstr(resource='kickerText'),ba.Lstr(resource='Motion')],
            current_choice='PCModder',
            delegate=self)
        self._popup_type = 'test'

    def _update(self) -> None:
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-nested-blocks

        # update muted state
        if ba.app.config.resolve('Chat Muted'):
            ba.textwidget(edit=self._muted_text, color=(1, 1, 1, 0.3))
            # clear any chat texts we're showing
            if self._chat_texts:
                while self._chat_texts:
                    first = self._chat_texts.pop()
                    first.delete()
        else:
            ba.textwidget(edit=self._muted_text, color=(1, 1, 1, 0.0))

        # update roster section
        roster = _ba.get_game_roster()
        if roster != self._roster:
            self._roster = roster

            # clear out old
            for widget in self._name_widgets:
                widget.delete()
            self._name_widgets = []
            if not self._roster:
                top_section_height = 60
                ba.textwidget(edit=self._empty_str,
                              text=ba.Lstr(resource=self._r + '.emptyText'))
                ba.scrollwidget(edit=self._scrollwidget,
                                size=(self._width - 50,
                                      self._height - top_section_height - 110),
                                position=(30, 80))
            else:
                columns = 1 if len(
                    self._roster) == 1 else 2 if len(self._roster) == 2 else 3
                rows = int(math.ceil(float(len(self._roster)) / columns))
                c_width = (self._width * 0.9) / max(3, columns)
                c_width_total = c_width * columns
                c_height = 24
                c_height_total = c_height * rows
                for y in range(rows):
                    for x in range(columns):
                        index = y * columns + x
                        if index < len(self._roster):
                            t_scale = 0.65
                            pos = (self._width * 0.53 - c_width_total * 0.5 +
                                   c_width * x - 23,
                                   self._height - 65 - c_height * y - 15)

                            # if there are players present for this client, use
                            # their names as a display string instead of the
                            # client spec-string
                            try:
                                if self._roster[index]['players']:
                                    # if there's just one, use the full name;
                                    # otherwise combine short names
                                    if len(self._roster[index]
                                           ['players']) == 1:
                                        p_str = self._roster[index]['players'][
                                            0]['name_full']
                                    else:
                                        p_str = ('/'.join([
                                            entry['name'] for entry in
                                            self._roster[index]['players']
                                        ]))
                                        if len(p_str) > 25:
                                            p_str = p_str[:25] + '...'
                                else:
                                    p_str = self._roster[index][
                                        'display_string']
                            except Exception:
                                ba.print_exception(
                                    'Error calcing client name str.')
                                p_str = '???'

                            widget = ba.textwidget(parent=self._root_widget,
                                                   position=(pos[0], pos[1]),
                                                   scale=t_scale,
                                                   size=(c_width * 0.85, 30),
                                                   maxwidth=c_width * 0.85,
                                                   color=(1, 1,
                                                          1) if index == 0 else
                                                   (1, 1, 1),
                                                   selectable=True,
                                                   autoselect=True,
                                                   click_activate=True,
                                                   text=ba.Lstr(value=p_str),
                                                   h_align='left',
                                                   v_align='center')
                            self._name_widgets.append(widget)

                            # in newer versions client_id will be present and
                            # we can use that to determine who the host is.
                            # in older versions we assume the first client is
                            # host
                            if self._roster[index]['client_id'] is not None:
                                is_host = self._roster[index][
                                    'client_id'] == -1
                            else:
                                is_host = (index == 0)

                            # FIXME: Should pass client_id to these sort of
                            #  calls; not spec-string (perhaps should wait till
                            #  client_id is more readily available though).
                            ba.textwidget(edit=widget,
                                          on_activate_call=ba.Call(
                                              self._on_party_member_press,
                                              self._roster[index]['client_id'],
                                              is_host, widget))
                            pos = (self._width * 0.53 - c_width_total * 0.5 +
                                   c_width * x,
                                   self._height - 65 - c_height * y)

                            # Make the assumption that the first roster
                            # entry is the server.
                            # FIXME: Shouldn't do this.
                            if is_host:
                                twd = min(
                                    c_width * 0.85,
                                    _ba.get_string_width(
                                        p_str, suppress_warning=True) *
                                    t_scale)
                                self._name_widgets.append(
                                    ba.textwidget(
                                        parent=self._root_widget,
                                        position=(pos[0] + twd + 1,
                                                  pos[1] - 0.5),
                                        size=(0, 0),
                                        h_align='left',
                                        v_align='center',
                                        maxwidth=c_width * 0.96 - twd,
                                        color=(0.1, 1, 0.1, 0.5),
                                        text=ba.Lstr(resource=self._r +
                                                     '.hostText'),
                                        scale=0.4,
                                        shadow=0.1,
                                        flatness=1.0))
                ba.textwidget(edit=self._empty_str, text='')
                ba.scrollwidget(edit=self._scrollwidget,
                                size=(self._width - 50,
                                      max(100, self._height - 139 -
                                          c_height_total)),
                                position=(30, 80))

    def popup_menu_selected_choice(self, popup_window: popup.PopupMenuWindow,
                                   choice: str) -> None:
        """Called when a choice is selected in the popup."""
        del popup_window  # unused
        if self._popup_type == 'partyMemberPress':
            if choice in ('KickVote'):
                result = _ba.disconnect_client(
                self._popup_party_member_client_id, ban_time=5 * 60)
                #_ba.chatmessage(str(self._popup_party_member_client_id)) thats how we get client id from string
                          
            elif choice in ('Kill'):
               # _ba.chatmessage(self._popup_party_member_client_id)
                for client in _ba.get_game_roster():
                    if client['client_id'] == self._popup_party_member_client_id:
                        try:
                            _ba.chatmessage("/kill "+ str(client['players'][0]['name'].lower()))
                        except:
                            pass
                            
            elif choice in ('PlayerKick'):
               # _ba.chatmessage(self._popup_party_member_client_id)
                for client in _ba.get_game_roster():
                    if client['client_id'] == self._popup_party_member_client_id:
                        try:
                            _ba.chatmessage("/kick "+ str(self._popup_party_member_client_id))#ALWAYS REMEMBER STRING THAT IS THE TRICK
                        except:
                            pass
                            
            elif choice in ('KickID'):
               # _ba.chatmessage(self._popup_party_member_client_id)
                for client in _ba.get_game_roster():
                    if client['client_id'] == self._popup_party_member_client_id:
                        try:
                            ba.screenmessage("KickID --->   "+ str(self._popup_party_member_client_id))#ALWAYS REMEMBER STRING THAT IS THE TRICK
                        except:
                            pass
                            
            elif choice in ('Curse'):
               # _ba.chatmessage(self._popup_party_member_client_id)
                for client in _ba.get_game_roster():
                    if client['client_id'] == self._popup_party_member_client_id:
                        try:
                            _ba.chatmessage("/curse "+ str(client['players'][0]['name'].lower()))
                        except:
                            pass
                            
            elif choice in ('Freeze'):
               # _ba.chatmessage(self._popup_party_member_client_id)
                for client in _ba.get_game_roster():
                    if client['client_id'] == self._popup_party_member_client_id:
                        try:
                            _ba.chatmessage("/freeze "+ str(client['players'][0]['name'].lower()))
                        except:
                            pass
                            
            elif choice in ('Punch'):
               # _ba.chatmessage(self._popup_party_member_client_id)
                for client in _ba.get_game_roster():
                    if client['client_id'] == self._popup_party_member_client_id:
                        try:
                            _ba.chatmessage("/punch "+ str(client['players'][0]['name'].lower()))
                        except:
                            pass
                            
            elif choice in ('Heal'):
               # _ba.chatmessage(self._popup_party_member_client_id)
                for client in _ba.get_game_roster():
                    if client['client_id'] == self._popup_party_member_client_id:
                        try:
                            _ba.chatmessage("/heal "+ str(client['players'][0]['name'].lower()))
                        except:
                            pass
                            
            elif choice in ('Remove'):
               # _ba.chatmessage(self._popup_party_member_client_id)
                for client in _ba.get_game_roster():
                    if client['client_id'] == self._popup_party_member_client_id:
                        try:
                            _ba.chatmessage("/remove "+ str(client['players'][0]['name'].lower()))
                        except:
                            pass
                            
            elif choice in ('Shield'):
               # _ba.chatmessage(self._popup_party_member_client_id)
                for client in _ba.get_game_roster():
                    if client['client_id'] == self._popup_party_member_client_id:
                        try:
                            _ba.chatmessage("/shield "+ str(client['players'][0]['name'].lower()))
                        except:
                            pass
                            
            elif choice in ('Thaw'):
               # _ba.chatmessage(self._popup_party_member_client_id)
                for client in _ba.get_game_roster():
                    if client['client_id'] == self._popup_party_member_client_id:
                        try:
                            _ba.chatmessage("/thaw "+ str(client['players'][0]['name'].lower()))
                        except:
                            pass
                            
        elif self._popup_type == 'menu':
            if choice in ('mute', 'unmute'):
                cfg = ba.app.config
                cfg['Chat Muted'] = (choice == 'mute')
                cfg.apply_and_commit()
                self._update()
        elif self._popup_type == 'test':
            if choice in ('PCModder'):
                _ba.chatmessage('Created by PC||Modder')
                self._update()
            elif choice in ('Motion'):
                _ba.chatmessage('/sm')
                self._update()
            elif choice in ('End'):
                _ba.chatmessage('/end')
                self._update()
            elif choice in ('Heal'):
                _ba.chatmessage('/heal all')
                self._update()
            elif choice in ('Punch'):
                _ba.chatmessage('/punch all')
                self._update()
            elif choice in ('Shield'):
                _ba.chatmessage('/shield all')
                self._update()
            elif choice in ('Hug'):
                _ba.chatmessage('/hug all')
                self._update()
            elif choice in ('Floater ON'):
                _ba.chatmessage('/floaterTrue')
                self._update()
            elif choice in ('Floater OFF'):
                _ba.chatmessage('/floaterFalse')
                self._update()
            elif choice in ('Whitelist ON'):
                _ba.chatmessage('/whiteTrue')
                self._update()
            elif choice in ('Whitelist OFF'):
                _ba.chatmessage('/whiteFalse')
                self._update()
            elif choice in ('Pwp ON'):
                _ba.chatmessage('/pwpTrue')
                self._update()
            elif choice in ('Pwp OFF'):
                _ba.chatmessage('/pwpFalse')
                self._update()
            elif choice in ('Powerups ON'):
                _ba.chatmessage('/powerupsTrue')
                self._update()
            elif choice in ('Powerups OFF'):
                _ba.chatmessage('/powerupsFalse')
                self._update()
            elif choice in ('PowerupNameON'):
                _ba.chatmessage('/powerupNameTrue')
                self._update()
            elif choice in ('PowerupNameOFF'):
                _ba.chatmessage('/powerupNameFalse')
                self._update()
            elif choice in ('DiscoLightON'):
                _ba.chatmessage('/discoLightTrue')
                self._update()
            elif choice in ('DiscoLight OFF'):
                _ba.chatmessage('/discoLightFalse')
                self._update()
            elif choice in ('PowerupShieldON'):
                _ba.chatmessage('/powerupShieldTrue')
                self._update()
            elif choice in ('PowerupShieldOFF'):
                _ba.chatmessage('/powerupShieldFalse')
                self._update()
            elif choice in ('BombModelON'):
                _ba.chatmessage('/bombModelTrue')
                self._update()
            elif choice in ('BombModelOFF'):
                _ba.chatmessage('/bombModelFalse')
                self._update()
            elif choice in ('BombNameON'):
                _ba.chatmessage('/bombNameTrue')
                self._update()
            elif choice in ('BombNameOFF'):
                _ba.chatmessage('/bombNameFalse')
                self._update()
            elif choice in ('Tag ON'):
                _ba.chatmessage('/tagTrue')
                self._update()
            elif choice in ('Tag OFF'):
                _ba.chatmessage('/tagFalse')
                self._update()
            elif choice in ('Animate ON'):
                _ba.chatmessage('/animateTrue')
                self._update()
            elif choice in ('Animate OFF'):
                _ba.chatmessage('/animateFalse')
                self._update()
            elif choice in ('Hp ON'):
                _ba.chatmessage('/hpTrue')
                self._update()
            elif choice in ('Hp OFF'):
                _ba.chatmessage('/hpFalse')
                self._update()
            elif choice in ('TeamMode ON'):
                _ba.chatmessage('/teamMode True')
                self._update()
            elif choice in ('FFAMode ON'):
                _ba.chatmessage('/ffaMode True')
                self._update()
            elif choice in ('Quit'):
                _ba.chatmessage('/quit')
                self._update()
            elif choice in ('Explo ON'):
                _ba.chatmessage('/ploTrue')
                self._update()
            elif choice in ('Explo OFF'):
                _ba.chatmessage('/ploFalse')
                self._update()
            elif choice in ('PopText ON'):
                _ba.chatmessage('/ptTrue')
                self._update()
            elif choice in ('PopText OFF'):
                _ba.chatmessage('/ptFalse')
                self._update()
            elif choice in ('Wizard ON'):
                _ba.chatmessage('/wizardfTrue')
                self._update()
            elif choice in ('Wizard OFF'):
                _ba.chatmessage('/wizardfFalse')
                self._update()
            elif choice in ('Pixie ON'):
                _ba.chatmessage('/pixiefTrue')
                self._update()
            elif choice in ('Pixie OFF'):
                _ba.chatmessage('/pixiefFalse')
                self._update()
            elif choice in ('Ninja ON'):
                _ba.chatmessage('/ninjafTrue')
                self._update()
            elif choice in ('Ninja OFF'):
                _ba.chatmessage('/ninjafFalse')
                self._update()
            elif choice in ('Frosty ON'):
                _ba.chatmessage('/frostyfTrue')
                self._update()
            elif choice in ('Frosty OFF'):
                _ba.chatmessage('/frostyfFalse')
                self._update()
            elif choice in ('Pengu ON'):
                _ba.chatmessage('/pengufTrue')
                self._update()
            elif choice in ('Pengu OFF'):
                _ba.chatmessage('/pengufFalse')
                self._update()
            elif choice in ('Ali ON'):
                _ba.chatmessage('/alifTrue')
                self._update()
            elif choice in ('Ali OFF'):
                _ba.chatmessage('/alifFalse')
                self._update()
            elif choice in ('Robot ON'):
                _ba.chatmessage('/robotfFalse')
                self._update()
            elif choice in ('Robot OFF'):
                _ba.chatmessage('/robotfFalse')
                self._update()
            elif choice in ('Santa ON'):
                _ba.chatmessage('/santafTrue')
                self._update()
            elif choice in ('Santa OFF'):
                _ba.chatmessage('/santafFalse')
                self._update()
            elif choice in ('Impact ON'):
                _ba.chatmessage('/impactfTrue')
                self._update()
            elif choice in ('Impact OFF'):
                _ba.chatmessage('/impactfFalse')
                self._update()
            elif choice in ('Ice ON'):
                _ba.chatmessage('/icefTrue')
                self._update()
            elif choice in ('Ice OFF'):
                _ba.chatmessage('/icefFalse')
                self._update()
            elif choice in ('Sticky ON'):
                _ba.chatmessage('/stickyfTrue')
                self._update()
            elif choice in ('Sticky OFF'):
                _ba.chatmessage('/stickyfFalse')
                self._update()
            elif choice in ('Spike ON'):
                _ba.chatmessage('/spikefTrue')
                self._update()
            elif choice in ('Spike OFF'):
                _ba.chatmessage('/spikefFalse')
                self._update()
            elif choice in ('Shock ON'):
                _ba.chatmessage('/shockfTrue')
                self._update()
            elif choice in ('Shock OFF'):
                _ba.chatmessage('/shockfFalse')
                self._update()
            elif choice in ('Knock ON'):
                _ba.chatmessage('/knockfTrue')
                self._update()
            elif choice in ('Knock OFF'):
                _ba.chatmessage('/knockfFalse')
                self._update()
            elif choice in ('Glue ON'):
                _ba.chatmessage('/gluefTrue')
                self._update()
            elif choice in ('Glue OFF'):
                _ba.chatmessage('/gluefFalse')
                self._update()
            elif choice in ('PWPIce ON'):
                _ba.chatmessage('/pwpicefTrue')
                self._update()
            elif choice in ('PWPIce OFF'):
                _ba.chatmessage('/pwpicefFalse')
                self._update()
            elif choice in ('PWPSplint ON'):
                _ba.chatmessage('/pwpsplintfTrue')
                self._update()
            elif choice in ('PWPSplint OFF'):
                _ba.chatmessage('/pwpsplintfFalse')
                self._update()
            elif choice in ('PWPSlime ON'):
                _ba.chatmessage('/pwpslimefTrue')
                self._update()
            elif choice in ('PWPSlime OFF'):
                _ba.chatmessage('/pwpslimefFalse')
                self._update()
            elif choice in ('PWPSweat ON'):
                _ba.chatmessage('/pwpsweatfTrue')
                self._update()
            elif choice in ('PWPSweat OFF'):
                _ba.chatmessage('/pwpsweatfFalse')
                self._update()
            elif choice in ('SlimeSnow'):
                _ba.chatmessage('/slimesnow 0')
                self._update()
            elif choice in ('SplinterSnow'):
                _ba.chatmessage('/splintersnow 0')
                self._update()
            elif choice in ('IceSnow'):
                _ba.chatmessage('/icesnow 0')
                self._update()
            elif choice in ('SparkSnow'):
                _ba.chatmessage('/sparksnow 0')
                self._update()
            elif choice in ('SweatSnow'):
                _ba.chatmessage('/sweatsnow 0')
                self._update()
            elif choice in ('NormalShower'):
                _ba.chatmessage('/normalshower 0')
                self._update()
            elif choice in ('StickyShower'):
                _ba.chatmessage('/stickyshower 0')
                self._update()
            elif choice in ('IceShower'):
                _ba.chatmessage('/iceshower 0')
                self._update()
            elif choice in ('GlueShower'):
                _ba.chatmessage('/glueshower 0')
                self._update()
            elif choice in ('CursyShower'):
                _ba.chatmessage('/cursyshower 0')
                self._update()
            elif choice in ('ImpactShower'):
                _ba.chatmessage('/impactshower 0')
                self._update()
            elif choice in ('FrozenShower'):
                _ba.chatmessage('/frozenshower 0')
                self._update()
            elif choice in ('PwpShower'):
                _ba.chatmessage('/pwpShower 0')
                self._update()
            elif choice in ('MAP_TEX'):
                _ba.chatmessage('Created by PC||Modder')
                self._update()
            elif choice in ('Pink'):
                _ba.chatmessage('/pink')
                self._update()
            elif choice in ('Snow'):
                _ba.chatmessage('/snow')
                self._update()
            elif choice in ('Snow2'):
                _ba.chatmessage('/snow2')
                self._update()
            elif choice in ('Blue'):
                _ba.chatmessage('/blue')
                self._update()
            elif choice in ('Red'):
                _ba.chatmessage('/red')
                self._update()
            elif choice in ('Red2'):
                _ba.chatmessage('/red2')
                self._update()
            elif choice in ('Red3'):
                _ba.chatmessage('/red3')
                self._update()
            elif choice in ('Red4'):
                _ba.chatmessage('/red4')
                self._update()
            elif choice in ('Orange'):
                _ba.chatmessage('/orange')
                self._update()
            elif choice in ('Orange2'):
                _ba.chatmessage('/orange2')
                self._update()
            elif choice in ('Yellow'):
                _ba.chatmessage('/yellow')
                self._update()
            elif choice in ('Dirt'):
                _ba.chatmessage('/dirt')
                self._update()
            elif choice in ('Dirt2'):
                _ba.chatmessage('/dirt2')
                self._update()
            elif choice in ('Dark'):
                _ba.chatmessage('/dark')
                self._update()
            elif choice in ('Smooth'):
                _ba.chatmessage('/smooth')
                self._update()
            elif choice in ('Smooth'):
                _ba.chatmessage('/smooth2')
                self._update()
            elif choice in ('Colorful'):
                _ba.chatmessage('/colorful')
                self._update()
        else:
            print(f'unhandled popup type: {self._popup_type}')

    def popup_menu_closing(self, popup_window: popup.PopupWindow) -> None:
        """Called when the popup is closing."""

    def _on_party_member_press(self, client_id: int, is_host: bool,
                               widget: ba.Widget) -> None:
        # if we're the host, pop up 'kick' options for all non-host members
        if _ba.get_foreground_host_session() is not None:
            kick_str = ba.Lstr(resource='kickText')
        else:
            # kick-votes appeared in build 14248
            if (_ba.get_connection_to_host_info().get('build_number', 0) <
                    14248):
                return
            kick_str = ba.Lstr(resource='kickVoteText')
        uiscale = ba.app.ui.uiscale
        popup.PopupMenuWindow(
            position=widget.get_screen_space_center(),
            scale=(2.3 if uiscale is ba.UIScale.SMALL else
                   1.65 if uiscale is ba.UIScale.MEDIUM else 1.23),
            choices=['KickVote','Kill','PlayerKick','KickID','Curse','Freeze','Punch','Shield','Heal','Remove','Thaw',],
            choices_display=[kick_str],
            current_choice='KickVote',
            delegate=self)
        self._popup_type = 'partyMemberPress'
        self._popup_party_member_client_id = client_id
        self._popup_party_member_is_host = is_host

    def _send_chat_message(self) -> None:
        _ba.chatmessage(cast(str, ba.textwidget(query=self._text_field)))
        ba.textwidget(edit=self._text_field, text='')

    def close(self) -> None:
        """Close the window."""
        ba.containerwidget(edit=self._root_widget, transition='out_scale')

    def close_with_sound(self) -> None:
        """Close the window and make a lovely sound."""
        ba.playsound(ba.getsound('swish'))
        self.close()


def handle_party_invite(name: str, invite_id: str) -> None:
    """Handle an incoming party invitation."""
    from bastd import mainmenu
    from bastd.ui import confirm
    ba.playsound(ba.getsound('fanfare'))

    # if we're not in the main menu, just print the invite
    # (don't want to screw up an in-progress game)
    in_game = not isinstance(_ba.get_foreground_host_session(),
                             mainmenu.MainMenuSession)
    if in_game:
        ba.screenmessage(ba.Lstr(
            value='${A}\n${B}',
            subs=[('${A}',
                   ba.Lstr(resource='gatherWindow.partyInviteText',
                           subs=[('${NAME}', name)])),
                  ('${B}',
                   ba.Lstr(
                       resource='gatherWindow.partyInviteGooglePlayExtraText'))
                  ]),
                         color=(0.5, 1, 0))
    else:

        def do_accept(inv_id: str) -> None:
            _ba.accept_party_invitation(inv_id)

        conf = confirm.ConfirmWindow(
            ba.Lstr(resource='gatherWindow.partyInviteText',
                    subs=[('${NAME}', name)]),
            ba.Call(do_accept, invite_id),
            width=500,
            height=150,
            color=(0.75, 1.0, 0.0),
            ok_text=ba.Lstr(resource='gatherWindow.partyInviteAcceptText'),
            cancel_text=ba.Lstr(resource='gatherWindow.partyInviteIgnoreText'))

        # FIXME: Ugly.
        # Let's store the invite-id away on the confirm window so we know if
        # we need to kill it later.
        conf.party_invite_id = invite_id  # type: ignore

        # store a weak-ref so we can get at this later
        ba.app.invite_confirm_windows.append(weakref.ref(conf))

        # go ahead and prune our weak refs while we're here.
        ba.app.invite_confirm_windows = [
            w for w in ba.app.invite_confirm_windows if w() is not None
        ]
