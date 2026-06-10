    def _open_ai_dialog(self, *_):
        if not self.ai_engine or not self.parent_window: return
        
        # Essayer de trouver project_root
        project_root = None
        # Le parent_window est souvent l'ApplicationWindow ou l'Application
        if hasattr(self.parent_window, 'project_root'):
            project_root = self.parent_window.project_root
        elif hasattr(self.parent_window, 'win') and hasattr(self.parent_window.win, 'project_root'): # Cas où parent_window est l'App
             project_root = self.parent_window.project_root # Si c'est l'app elle-même
             
        # Si ça ne marche pas, on peut essayer de le deviner depuis le fichier courant
        if not project_root and self.file_ext: 
             # Ceci est une approximation, mieux vaut le passer explicitement
             pass 

        def on_confirm(block, new_code):
            self.block["code"] = new_code
            self.on_save_cb(self.block, new_code)
            self.textview.get_buffer().set_text(new_code)
            apply_syntax_highlighting(self.textview, self.lang)
            # Toast notification might need adjustment depending on where toast is shown
            if hasattr(self.parent_window, '_show_toast'):
                self.parent_window._show_toast("✅ Bloc modifié par IA")

        dialog = AIModificationDialog(self.parent_window, self.block, self.ai_engine, on_confirm, project_root=project_root)
        dialog.present()
