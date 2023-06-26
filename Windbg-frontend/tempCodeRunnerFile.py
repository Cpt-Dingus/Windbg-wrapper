      if jim_mode:
            dark_style.theme_use('dark')
            main_message("Dark mode enabled, welcome home.")

        # Light mode
        else:
            dark_style.theme_use('default')
            main_message("Light mode enabled, may your eyes burn.")