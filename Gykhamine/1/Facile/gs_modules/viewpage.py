import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, Gio
import sys, os

from .utils import (
    CSS, lbl, btn, combo, entry, hbox, vbox, 
    scroll_wrap, margins, Gen
)
from .genpage import GenPage

class ViewPage(GenPage):
    def __init__(self):
        super().__init__("Vue")
        # 1. IDENTITÉ
        self.form_box.append(self._section("IDENTITÉ DE LA VUE"))
        g = Gtk.Grid()
        g.set_column_spacing(10); g.set_row_spacing(8)
        self.e_name  = entry("nom_vue", "article_list")
        self.e_model = entry("NomModele", "Article")
        self.e_url_params = entry("pk, slug", "")
        self.e_url_params.set_placeholder_text("Paramètres URL (ex: pk, slug)")
        g.attach(lbl("Nom de la vue:"),    0,0,1,1); g.attach(self.e_name,      1,0,1,1)
        g.attach(lbl("Modèle lié:"),       0,1,1,1); g.attach(self.e_model,     1,1,1,1)
        g.attach(lbl("Params URL:"),       0,2,1,1); g.attach(self.e_url_params,1,2,1,1)
        self.form_box.append(g)
        # 2. DÉCORATEURS
        self.form_box.append(self._section("DÉCORATEURS"))
        self.dec_checks = {}
        dec_grid = Gtk.Grid()
        dec_grid.set_column_spacing(8); dec_grid.set_row_spacing(4)
        for i, (did, dlabel) in enumerate(Gen.DECORATORS):
            chk = Gtk.CheckButton.new_with_label(dlabel)
            chk.connect("toggled", self._gen)
            self.dec_checks[did] = chk
        dec_grid.attach(chk, i%2, i//2, 1, 1)
        if 'login_required' in self.dec_checks:
            self.dec_checks['login_required'].set_active(True)
        self.form_box.append(dec_grid)
        # 3. MÉTHODE HTTP
        self.form_box.append(self._section("MÉTHODE HTTP"))
        self.c_method = combo([("ANY","Toutes"), ("GET","GET"), ("POST","POST"),
                               ("PUT","PUT"), ("PATCH","PATCH"), ("DELETE","DELETE")])
        self.c_method.connect("changed", self._gen)
        self.form_box.append(self.c_method)
        # 4. ORM MULTI-OPÉRATIONS (CHAINAGE)
        self.form_box.append(self._section("OPÉRATIONS ORM (CHAINAGE)"))
        self.orm_ops_box = vbox(4)
        self.form_box.append(self.orm_ops_box)
        btn_add_orm = btn("➕ Ajouter Opération ORM", "suggested-action", self._add_orm_op)
        self.form_box.append(btn_add_orm)
        # 5. STRUCTURE DE RÉPONSE (VARIABLES)
        self.form_box.append(self._section("STRUCTURE DES DONNÉES DE RÉPONSE"))
        resp_struct_box = vbox(6)
        r1 = hbox(6)
        r1.append(lbl("Variable principale:"))
        self.e_resp_var = entry("data", "objects")
        self.e_resp_var.set_width_chars(10)
        r1.append(self.e_resp_var)
        r1.append(lbl("Type de structure:"))
        self.c_resp_struct = combo([
            ("dict", "Dictionnaire {key: val}"),
            ("list", "Liste [val1, val2]"),
            ("tuple", "Tuple (val1, val2)"),
            ("set", "Set {val1, val2}"),
            ("simple", "Variable Simple")
        ])
        r1.append(self.c_resp_struct)
        resp_struct_box.append(r1)
        # Zone pour les paires clé/valeur ou éléments selon le type
        self.resp_fields_box = vbox(4)
        resp_struct_box.append(self.resp_fields_box)
        self.form_box.append(resp_struct_box)
        # Connecteurs pour mettre à jour l'interface selon le type
        self.c_resp_struct.connect("changed", self._update_resp_fields)
        self.e_resp_var.connect("changed", self._gen)
        # 6. TYPE DE RÉPONSE HTTP
        self.form_box.append(self._section("TYPE DE RÉPONSE HTTP"))
        self.c_resp = combo(Gen.RESPONSE_TYPES)
        self.c_resp.connect("changed", self._gen)
        self.form_box.append(self.c_resp)
        # 7. LOGIQUE PERSONNALISÉE
        self.form_box.append(self._section("LOGIQUE & APPELS DE MÉTHODES"))
        self.custom_logic_box = vbox(4)
        self.form_box.append(self.custom_logic_box)
        btn_add_custom = btn("➕ Ajouter Bloc Logique", None, self._add_custom_logic)
        self.form_box.append(btn_add_custom)
        # 8. VÉRIFICATIONS STANDARDS
        self.form_box.append(self._section("VÉRIFICATIONS STANDARDS"))
        self.logic_box = vbox(4)
        self.form_box.append(self.logic_box)
        self.form_box.append(btn("➕ Ajouter Vérification", None, self._add_logic))
        for w in (self.e_name, self.e_model, self.e_url_params):
            w.connect("changed", self._gen)
        # Init avec une opération ORM par défaut
        self._add_orm_op()
        self._update_resp_fields()
        self._gen()

    def _add_orm_op(self, *_):
        row = hbox(6)
        row.add_css_class("field-row")
        # Liste étendue des opérations ORM
        ops = [
            ("none", "— Sélectionner —"),
            ("all", ".all()"),
            ("filter", ".filter(...)"),
            ("exclude", ".exclude(...)"),
            ("order_by", ".order_by(...)"),
            ("distinct", ".distinct()"),
            ("select_related", ".select_related(...)"),
            ("prefetch_related", ".prefetch_related(...)"),
            ("only", ".only(...)"),
            ("defer", ".defer(...)"),
            ("values", ".values(...)"),
            ("values_list", ".values_list(...)"),
            ("annotate", ".annotate(...)"),
            ("aggregate", ".aggregate(...)"),
            ("count", ".count()"),
            ("exists", ".exists()"),
            ("first", ".first()"),
            ("last", ".last()"),
            ("get", ".get(...)"),
            ("create", ".create(...)"),
            ("bulk_create", ".bulk_create(...)"),
            ("update", ".update(...)"),
            ("delete", ".delete()"),
            ("raw", ".raw(...)"),
            ("union", ".union(...)"),
            ("intersection", ".intersection(...)"),
            ("difference", ".difference(...)"),
        ]
        c_op = combo(ops)
        c_op.set_size_request(150, -1)
        e_args = entry("arguments (ex: actif=True, '-date')")
        e_args.set_hexpand(True)
        b = btn("✕", "destructive-action", lambda w: (self.orm_ops_box.remove(row), self._gen()))
        for w in (c_op, e_args):
            w.connect("changed", self._gen)
        row.append(c_op)
        row.append(e_args)
        row.append(b)
        self.orm_ops_box.append(row)
        self._gen()

    def _update_resp_fields(self, *_):
        # Nettoyer la zone
        while self.resp_fields_box.get_first_child():
            self.resp_fields_box.remove(self.resp_fields_box.get_first_child())
        struct_type = self.c_resp_struct.get_active_id()
        if struct_type == 'dict':
            lbl_info = lbl("Définissez les clés et valeurs du dictionnaire de contexte:")
            self.resp_fields_box.append(lbl_info)
            # Bouton pour ajouter une paire clé/valeur (toujours ajouté en dernier)
            self.btn_add_pair = btn("➕ Ajouter Clé/Valeur", None, self._add_resp_pair)
            self.resp_fields_box.append(self.btn_add_pair)
            # Ajouter une paire par défaut si vide
            self._add_resp_pair()
        elif struct_type == 'list':
            lbl_info = lbl("Les éléments seront ajoutés à une liste:")
            self.resp_fields_box.append(lbl_info)
            e_item = entry("élément (ex: obj.nom)")
            e_item.connect("changed", self._gen)
            self.resp_fields_box.append(e_item)
        elif struct_type == 'tuple':
            lbl_info = lbl("Définissez les éléments du tuple séparés par des virgules:")
            self.resp_fields_box.append(lbl_info)
            e_items = entry("elem1, elem2, elem3")
            e_items.connect("changed", self._gen)
            self.resp_fields_box.append(e_items)
        elif struct_type == 'set':
            lbl_info = lbl("Définissez les éléments du set séparés par des virgules:")
            self.resp_fields_box.append(lbl_info)
            e_items = entry("elem1, elem2, elem3")
            e_items.connect("changed", self._gen)
            self.resp_fields_box.append(e_items)
        elif struct_type == 'simple':
            lbl_info = lbl("La variable contiendra une valeur simple:")
            self.resp_fields_box.append(lbl_info)
            e_val = entry("valeur (ex: obj.nom)")
            e_val.connect("changed", self._gen)
            self.resp_fields_box.append(e_val)
        self._gen()

    def _add_resp_pair(self, *_):
        row = hbox(6)
        row.add_css_class("field-row")
        e_key = entry("clé (ex: 'articles')")
        e_key.set_width_chars(12)
        e_val = entry("valeur (ex: objects)")
        e_val.set_hexpand(True)
        b = btn("✕", "destructive-action", lambda w: (self.resp_fields_box.remove(row), self._gen()))
        for w in (e_key, e_val):
            w.connect("changed", self._gen)
        row.append(e_key)
        row.append(e_val)
        row.append(b)
        # Insertion avant le bouton "Ajouter" s'il existe
        if hasattr(self, 'btn_add_pair') and self.btn_add_pair:
            prev_sibling = self.btn_add_pair.get_prev_sibling()
            if prev_sibling:
                self.resp_fields_box.insert_child_after(row, prev_sibling)
            else:
                self.resp_fields_box.remove(self.btn_add_pair)
                self.resp_fields_box.append(row)
                self.resp_fields_box.append(self.btn_add_pair)
        else:
            self.resp_fields_box.append(row)
        self._gen()

    def _add_custom_logic(self, *_):
        """Ajoute un bloc logique avec Condition ET Actions (Méthodes directes)"""
        row = vbox(4)
        row.add_css_class("logic-block")
        # Ligne 1 : Type de structure
        r1 = hbox(6)
        c_type = combo([
            ("if", "Si (if)"),
            ("elif", "Sinon Si (elif)"),
            ("else", "Sinon (else)"),
            ("for", "Boucle (for)"),
            ("while", "Boucle (while)"),
            ("assign", "Définir Variable"),
            ("return", "Retourner Valeur"),
        ])
        c_type.set_size_request(120, -1)
        # Champs de condition (dynamiques)
        params_box = hbox(6)
        e_cond = entry("condition (ex: x > 10)")
        e_iter = entry("itérable (ex: range(10))")
        e_var = entry("variable")
        e_val = entry("valeur")
        row._type = c_type
        row._params = (e_cond, e_iter, e_var, e_val)
        # Ligne 2 : Actions imbriquées (Appels de méthodes directs)
        actions_box = vbox(2)
        actions_box.set_margin_start(20) # Indentation visuelle
        def update_params(*_):
            t = c_type.get_active_id()
            while params_box.get_first_child():
                params_box.remove(params_box.get_first_child())
            if t in ('if', 'elif', 'while'):
                params_box.append(lbl("Condition:")); params_box.append(e_cond)
            elif t == 'for':
                params_box.append(lbl("Variable:")); params_box.append(e_var)
                params_box.append(lbl("dans:")); params_box.append(e_iter)
            elif t == 'assign':
                params_box.append(lbl("Variable:")); params_box.append(e_var)
                params_box.append(lbl("=")); params_box.append(e_val)
            elif t == 'return':
                params_box.append(lbl("Valeur:")); params_box.append(e_val)
            self._gen()
        c_type.connect("changed", update_params)
        # Bouton pour ajouter une méthode/action dans ce bloc
        btn_add_action = btn("➕ Méthode/Fonction", "suggested-action",
                             lambda w: self._add_method_to_block(actions_box))
        r1.append(c_type)
        r1.append(params_box)
        r1.append(btn_add_action)
        row.append(r1)
        row.append(actions_box)
        # Bouton supprimer le bloc entier
        btn_del = btn("✕ Supprimer Bloc", "destructive-action",
                      lambda w: (self.custom_logic_box.remove(row), self._gen()))
        row.append(btn_del)
        update_params()
        self.custom_logic_box.append(row)
        self._gen()

    def _add_method_to_block(self, parent_box):
        """Ajoute une ligne pour écrire directement le nom de la fonction et ses paramètres"""
        action_row = hbox(6)
        action_row.add_css_class("field-row")
        # Champ pour le nom de la fonction/méthode
        e_func_name = entry("nom_fonction()")
        e_func_name.set_placeholder_text("ex: ma_fonction(a, b)")
        e_func_name.set_hexpand(True)
        # Champ optionnel pour des détails supplémentaires ou commentaires
        e_detail = entry("détail / commentaire")
        e_detail.set_width_chars(15)
        b = btn("✕", "destructive-action", lambda w: (parent_box.remove(action_row), self._gen()))
        for w in (e_func_name, e_detail):
            w.connect("changed", self._gen)
        action_row.append(lbl("Appel:"))
        action_row.append(e_func_name)
        action_row.append(e_detail)
        action_row.append(b)
        parent_box.append(action_row)
        self._gen()

    def _add_logic(self, *_):
        row = hbox(6)
        row.add_css_class("logic-block")
        actions = [
            ("check_auth", "Vérifier Authentification"),
            ("check_param", "Vérifier Paramètre GET"),
            ("check_post_field", "Vérifier Champ POST"),
            ("log_action", "Journaliser l'action"),
        ]
        c = combo(actions)
        e = entry("détail")
        e.set_width_chars(15)
        b = btn("✕", "destructive-action", lambda w: (self.logic_box.remove(row), self._gen()))
        row._widgets = (c, e)
        c.connect("changed", self._gen); e.connect("changed", self._gen)
        row.append(c); row.append(e); row.append(b)
        self.logic_box.append(row)
        self._gen()

    def _gen(self, *_):
        decorators = [did for did, chk in self.dec_checks.items() if chk.get_active()]
        # 1. Construction des opérations ORM
        orm_lines = []
        model_name = self.e_model.get_text() or "MonModele"
        current_var = f"{model_name}.objects"
        child = self.orm_ops_box.get_first_child()
        while child:
            if isinstance(child, Gtk.Box) and child.get_first_child():
                c_op = child.get_first_child()
                e_args = c_op.get_next_sibling()
                if isinstance(c_op, Gtk.ComboBoxText) and isinstance(e_args, Gtk.Entry):
                    op_id = c_op.get_active_id()
                    args = e_args.get_text().strip()
                    if op_id and op_id != 'none':
                        if args:
                            # Gestion spéciale pour les arguments multiples ou complexes
                            if op_id in ['filter', 'exclude', 'get', 'create', 'update', 'aggregate', 'annotate']:
                                orm_lines.append(f"    {current_var} = {current_var}.{op_id}({args})")
                            elif op_id in ['order_by', 'select_related', 'prefetch_related', 'only', 'defer', 'values', 'values_list']:
                                # Ces méthodes prennent souvent des strings ou des champs
                                orm_lines.append(f"    {current_var} = {current_var}.{op_id}({args})")
                            else:
                                orm_lines.append(f"    {current_var} = {current_var}.{op_id}({args})")
                        else:
                            orm_lines.append(f"    {current_var} = {current_var}.{op_id}()")
            child = child.get_next_sibling()
        # Si aucune opération n'a été définie, on garde .objects par défaut ou on ajoute .all()
        if not orm_lines and model_name:
            orm_lines.append(f"    {current_var} = {current_var}.all()")
        final_orm_var = current_var # La dernière variable utilisée
        # 2. Construction de la structure de réponse
        resp_var_name = self.e_resp_var.get_text() or "data"
        resp_struct_type = self.c_resp_struct.get_active_id()
        resp_assignment_lines = []
        context_dict_str = "{}"
        if resp_struct_type == 'dict':
            pairs = []
            child = self.resp_fields_box.get_first_child()
            while child:
                if isinstance(child, Gtk.Box) and child.get_first_child():
                    e_key = child.get_first_child()
                    e_val = e_key.get_next_sibling()
                    if isinstance(e_key, Gtk.Entry) and isinstance(e_val, Gtk.Entry):
                        k = e_key.get_text().strip()
                        v = e_val.get_text().strip()
                        if k and v:
                            # Nettoyer les quotes si l'utilisateur les a mises
                            if not k.startswith("'") and not k.startswith('"'):
                                k = f"'{k}'"
                            pairs.append(f"{k}: {v}")
                child = child.get_next_sibling()
            if pairs:
                dict_content = ", ".join(pairs)
                resp_assignment_lines.append(f"    {resp_var_name} = {{{dict_content}}}")
                context_dict_str = resp_var_name
            else:
                resp_assignment_lines.append(f"    {resp_var_name} = {{}}")
                context_dict_str = resp_var_name
        elif resp_struct_type == 'list':
            child = self.resp_fields_box.get_first_child()
            # Le premier enfant est le label, le deuxième est l'entry
            e_item = child.get_next_sibling() if child else None
            if isinstance(e_item, Gtk.Entry):
                item_val = e_item.get_text().strip()
                if item_val:
                    resp_assignment_lines.append(f"    {resp_var_name} = [{item_val}]")
                else:
                    resp_assignment_lines.append(f"    {resp_var_name} = []")
                context_dict_str = f"{{'{resp_var_name}': {resp_var_name}}}"
            else:
                resp_assignment_lines.append(f"    {resp_var_name} = []")
                context_dict_str = f"{{'{resp_var_name}': {resp_var_name}}}"
        elif resp_struct_type == 'tuple':
            child = self.resp_fields_box.get_first_child()
            e_items = child.get_next_sibling() if child else None
            if isinstance(e_items, Gtk.Entry):
                items_val = e_items.get_text().strip()
                if items_val:
                    resp_assignment_lines.append(f"    {resp_var_name} = ({items_val})")
                else:
                    resp_assignment_lines.append(f"    {resp_var_name} = ()")
                context_dict_str = f"{{'{resp_var_name}': {resp_var_name}}}"
            else:
                resp_assignment_lines.append(f"    {resp_var_name} = ()")
                context_dict_str = f"{{'{resp_var_name}': {resp_var_name}}}"
        elif resp_struct_type == 'set':
            child = self.resp_fields_box.get_first_child()
            e_items = child.get_next_sibling() if child else None
            if isinstance(e_items, Gtk.Entry):
                items_val = e_items.get_text().strip()
                if items_val:
                    resp_assignment_lines.append(f"    {resp_var_name} = {{{items_val}}}")
                else:
                    resp_assignment_lines.append(f"    {resp_var_name} = set()")
                context_dict_str = f"{{'{resp_var_name}': {resp_var_name}}}"
            else:
                resp_assignment_lines.append(f"    {resp_var_name} = set()")
                context_dict_str = f"{{'{resp_var_name}': {resp_var_name}}}"
        elif resp_struct_type == 'simple':
            child = self.resp_fields_box.get_first_child()
            e_val = child.get_next_sibling() if child else None
            if isinstance(e_val, Gtk.Entry):
                val = e_val.get_text().strip()
                if val:
                    resp_assignment_lines.append(f"    {resp_var_name} = {val}")
                else:
                    resp_assignment_lines.append(f"    {resp_var_name} = None")
                context_dict_str = f"{{'{resp_var_name}': {resp_var_name}}}"
            else:
                resp_assignment_lines.append(f"    {resp_var_name} = None")
                context_dict_str = f"{{'{resp_var_name}': {resp_var_name}}}"
        # 3. Logique personnalisée
        custom_methods = []
        if hasattr(self, 'custom_logic_box'):
            child = self.custom_logic_box.get_first_child()
            while child:
                if hasattr(child, '_type'):
                    c_type = child._type
                    e_cond, e_iter, e_var, e_val = child._params
                    actions = []
                    actions_box = child.get_first_child().get_next_sibling()
                    if actions_box:
                        act_child = actions_box.get_first_child()
                        while act_child:
                            if isinstance(act_child, Gtk.Box):
                                lbl_w = act_child.get_first_child()
                                e_func = lbl_w.get_next_sibling() if lbl_w else None
                                e_det = e_func.get_next_sibling() if e_func else None
                                if isinstance(e_func, Gtk.Entry):
                                    actions.append({
                                        'type': 'method_call',
                                        'detail': e_func.get_text(),
                                        'comment': e_det.get_text() if isinstance(e_det, Gtk.Entry) else ""
                                    })
                            act_child = act_child.get_next_sibling()
                    custom_methods.append({
                        'type': c_type.get_active_id(),
                        'condition': e_cond.get_text(),
                        'iterable': e_iter.get_text(),
                        'var': e_var.get_text(),
                        'value': e_val.get_text(),
                        'actions': actions
                    })
                child = child.get_next_sibling()
        # 4. Logique standard
        logic = []
        if hasattr(self, 'logic_box'):
            child = self.logic_box.get_first_child()
            while child:
                if hasattr(child, '_widgets'):
                    c, e = child._widgets
                    logic.append({'action': c.get_active_id(), 'detail': e.get_text()})
                child = child.get_next_sibling()
        # Appel au générateur principal avec les nouvelles structures
        self._generate_full_code(decorators, orm_lines, resp_assignment_lines, context_dict_str, custom_methods, logic)

    def _generate_full_code(self, decorators, orm_lines, resp_assignment_lines, context_dict_str, custom_methods, logic):
        """Génère le code complet de la vue en assemblant les parties."""
        imports = [
            "from django.shortcuts import render, redirect, get_object_or_404",
            "from django.http import HttpResponse, JsonResponse, FileResponse, Http404",
            "from django.contrib import messages",
            "from django.core.paginator import Paginator",
            "from django.db.models import Q",
        ]
        dec_imports = {
            'login_required':       "from django.contrib.auth.decorators import login_required",
            'staff_member_required':"from django.contrib.admin.views.decorators import staff_member_required",
            'permission_required':  "from django.contrib.auth.decorators import permission_required",
            'cache_page':           "from django.views.decorators.cache import cache_page",
            'require_http_methods': "from django.views.decorators.http import require_http_methods",
            'csrf_exempt':          "from django.views.decorators.csrf import csrf_exempt",
            'transaction_atomic':   "from django.db import transaction",
        }
        for d in decorators:
            if d in dec_imports: imports.append(dec_imports[d])
        model_name = self.e_model.get_text()
        if model_name:
            imports.append(f"from .models import {model_name}")
        lines = imports + [""]
        # Décorateurs
        for d in decorators:
            if d == 'login_required':       lines.append("@login_required")
            elif d == 'staff_member_required': lines.append("@staff_member_required")
            elif d == 'permission_required': lines.append("@permission_required('app.can_view')")
            elif d == 'cache_page':         lines.append("@cache_page(60 * 15)")
            elif d == 'require_http_methods':
                method = self.c_method.get_active_id() or "GET"
                lines.append(f"@require_http_methods(['{method}'])")
            elif d == 'csrf_exempt':        lines.append("@csrf_exempt")
            elif d == 'transaction_atomic': lines.append("@transaction.atomic")
        # Signature
        params = ["request"] + [p.strip() for p in self.e_url_params.get_text().split(',') if p.strip()]
        view_name = self.e_name.get_text() or "ma_vue"
        lines.append(f"def {view_name}({', '.join(params)}):")
        # Méthode HTTP check si pas de décorateur
        method = self.c_method.get_active_id() or "ANY"
        if method != 'ANY' and 'require_http_methods' not in decorators:
            lines += [f"    if request.method != '{method}':", "        return HttpResponse('Method Not Allowed', status=405)"]
        # Opérations ORM
        lines.extend(orm_lines)
        # Logique personnalisée
        if custom_methods:
            for m in custom_methods:
                lines.extend(Gen._generate_custom_method(m, indent=4))
        # Logique standard
        for b in logic:
            if b.get('action') == 'check_auth':
                lines += ["    if not request.user.is_authenticated:", "        return redirect('login')"]
            elif b.get('action') == 'check_param':
                p = b.get('detail','param')
                lines += [f"    {p} = request.GET.get('{p}')", f"    if not {p}:", f"        return HttpResponse('Paramètre manquant', status=400)"]
            elif b.get('action') == 'check_post_field':
                p = b.get('detail','champ')
                lines += [f"    {p} = request.POST.get('{p}','')", f"    if not {p}:", f"        messages.error(request, '{p} est requis.')"]
            elif b.get('action') == 'log_action':
                lines += ["    import logging", "    logger = logging.getLogger(__name__)", f"    logger.info('Vue {view_name} appelée')"]
        # Assignation de la structure de réponse
        lines.extend(resp_assignment_lines)
        # Réponse HTTP
        response_type = self.c_resp.get_active_id() or "render"
        resp_var_name = self.e_resp_var.get_text() or "data"
        if response_type == 'render':
            template_name = f"{view_name}.html"
            lines.append(f"    return render(request, '{template_name}', {context_dict_str})")
        elif response_type == 'json':
            lines.append(f"    return JsonResponse({context_dict_str})")
        elif response_type == 'redirect':
            lines.append(f"    return redirect('nom_de_la_vue')")
        elif response_type == 'file':
            lines.append(f"    return FileResponse(open('chemin/fichier.pdf', 'rb'))")
        elif response_type == 'pdf':
            lines += ["    response = HttpResponse(content_type='application/pdf')",
                      "    response['Content-Disposition'] = 'attachment; filename=\"rapport.pdf\"'",
                      "    return response"]
        elif response_type == 'http':
            lines.append(f"    return HttpResponse('OK: {resp_var_name}')")
        elif response_type == 'error_404':
            lines.append("    raise Http404('Ressource introuvable.')")
        elif response_type == 'error_403':
            lines += ["    from django.core.exceptions import PermissionDenied", "    raise PermissionDenied"]
        self.set_code('\n'.join(lines))