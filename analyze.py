import argparse, os, sys
import fb_disassemble as fb
from tqdm import tqdm

class Dialogs:
    def __init__(self):
        self.output_file_name = ""
        self.output_path = ""
        self.anonymize = False

    
    def select_chats_percentage(self, inbox):
        self.print_stats_and_times(inbox)
        while True:
            # TODO: so it won't crash when you misstype
            i = int(input("Input percentage of users to be selected: "))
            inbox.select_based_on_percentage(i)
            print()
            self.print_stats_and_times(inbox)
            print()
            if self.ask_Y_n("Continue?"):
                break
    
    def select_chats_type(self, inbox):
        self.print_stats_and_times(inbox)
        selection = [
            ("")
        ]
        while True:
            inbox.select_based_on_percentage(i)
            print()
            self.print_stats_and_times(inbox)
            print()
            if self.ask_Y_n("Continue?"):
                break            
    
    def print_stats_and_times(self, inbox):
        print(inbox.get_stats())
        print(inbox.get_times())
    
    def print_numbered_menu(self, menu):
        while True:
            i = 0
            for item in menu:
                i += 1
                print(f'{i}. {item}')
            if i == 1:
                print("Chose 1: ", end="")
            else:
                print(f"Chose 1 to {i}: ", end="")
            u_in = input()
            if u_in.isdigit():
                u_in = int(u_in)
                if u_in >= 1 and u_in <= i:
                    return u_in
                else:
                    print("\nInput must be within the said range")
            else:
                print("\nOnly digits allowed")
    
    def print_numbered_menu_return_result(self, methods):
        menu = []
        for method in methods:
            menu.append(method[0])
        return methods[self.print_numbered_menu(menu) - 1][1]

    def print_numbered_menu_and_execute(self, methods, include_back = False):
        if include_back:
            methods.append(("Go back", "__back"))
        output = self.print_numbered_menu_return_result(methods)
        print()
        if "__back" in output:
            return True
        if isinstance(output, list):
            for out in output:
                if isinstance(out, tuple):
                    out[0](out[1])
                else:
                    out()
        else:
            out = output
            if isinstance(out, tuple):
                out[0](out[1])
            else:
                out()
    
   
    def output_file_name_set(self):
        if self.output_file_name == "":
            print("Output file name not yet specified")
            self.output_file_name = input("Enter output file name (without extension): ")
        else:
            print(f'Current output file name is: {self.output_file_name}')
            if not self.ask_Y_n("Do you want to keep it?"):
                self.output_file_name = input("Enter output file name (without extension): ")
    
    def create_output_folder(self, path):
        if not os.access(path, os.F_OK):
            os.mkdir(path)
            print("Created folder", end=" ")
        else: 
            print("Using existing output folder", end=" ")
        print(path + '/')

    def check_output_file(self, path):
        if os.path.isfile(path):
            if not self.ask_Y_n(f'File {self.cut_file_name(path)} already exist. Overwrite?'):
                return False
        with open(path, "w") as _:
            pass
        print(f"File {self.cut_file_name(path)} created")
        return True
    
    def cut_file_name(self, path):
        return path[path.rindex("/") + 1:]
    
    
    def abort(self):
        print("Aborting")
        sys.exit()

    def ask_Y_n(self, message = ""):
        print(f"{message} [Y/n] ", end='')
        resp = input().lower()
        if "n" in resp:
            return False
        return True

class Analyze:
    def __init__(self, diags):
        self.diags = diags

    def save_graph(self, inbox):
        self.diags.output_file_name_set()

        out_path = os.path.join(self.diags.output_path, self.diags.output_file_name)
        self.diags.create_output_folder(out_path)

        csv_path = os.path.join(out_path, self.diags.output_file_name + ".csv")
        meta_path = os.path.join(out_path, self.diags.output_file_name + "_meta.txt")
        if not self.diags.check_output_file(csv_path): return
        if not self.diags.check_output_file(meta_path): return
        print()

        self.diags.select_chats(inbox)

        period = int(input("\nEnter the number of days for a window: "))
        period = period * 24 * 3600 * 1000
        periods_count = int(inbox.meta.period / period) + 1
        periods_meta = f'{fb.convert_ms_year(inbox.meta.period)} years split into {periods_count} periods'
        print(periods_meta)

        print("Counting messages...\n")
        names_vals = {}
        # go through all chats...
        for chat in inbox.get_selected():          
            # initiate the dictionary
            key = chat.index_verbose if self.diags.anonymize else chat.name
            names_vals[key] = []
            for i in range(periods_count - 1):
                names_vals[key].append(0)
            
            # ...and the entire periods_count and count the number of messages per each period
            for period_num in range(periods_count - 1):
                
                lowest = inbox.meta.oldest_timestamp + (period_num * period)
                highest = inbox.meta.oldest_timestamp + ((period_num + 1) * period)
                
                for message in chat.messages:
                    if "timestamp_ms" in message:
                        ms = message["timestamp_ms"]
                        if ms >= lowest and ms < highest:
                            names_vals[key][period_num] += 1
        
        date_list = []
        combined = []
        for i in range(periods_count - 1):
            sum = 0
            for name in names_vals:
                sum += names_vals[name][i]
            combined.append(sum)
            #FIXME: (make nicer) cut just the date
            date = (fb.convert_ms(inbox.meta.oldest_timestamp + (i * period)))[0:10]
            date_list.append(date)
        # add "combined" to the dict, add "date" key as the last line
        names_vals["combined"], names_vals["date"] = combined, date_list
        
        print("Writing data to the file...")
        with open(csv_path, "w", encoding="utf-8") as file_out:
            for chat in names_vals:
                file_out.write(fb.remove_diacritic(chat) + ";")
                for val in names_vals[chat]:
                    file_out.write(f'{val};')
                file_out.write("\n")

        print("Writing meta info...")
        with open(meta_path, "w", encoding="utf-8") as file_out:
            file_out.write(inbox.get_stats() + "\n")
            file_out.write(inbox.get_times())
            file_out.write(f'{periods_meta} ({period} days per period)\n')
            
            file_out.write("\nIncluded in the graph (selected users):\n")
            for chat in inbox.get_selected():
                if self.diags.anonymize:
                    file_out.write(chat.index_verbose)
                else:
                    file_out.write(chat.name)
                file_out.write(f'\n{chat.get_stats()}\n')

    def save_most_used(self, inbox):
        self.diags.output_file_name_set()

        out_path = os.path.join(self.diags.output_path, self.diags.output_file_name)
        self.diags.create_output_folder(out_path)

        list_path = os.path.join(out_path, self.diags.output_file_name + ".txt")
        if not self.diags.check_output_file(list_path): return

        selected_names = []
        options = [
            ("All chats", [(inbox.select_based_on_percentage, 100), (self.diags.print_stats_and_times, inbox)]),
            ("Only selected chats", (self.diags.select_chats_percentage, inbox)),
            ("Leave the current selection", (self.diags.print_stats_and_times, inbox)),
            ("Only the sender (uses the current selection)", (selected_names.append, inbox.chats[0].meta.participants[1]))
        ]
        print()
        if self.diags.print_numbered_menu_and_execute(options, True):
            return

        print("Scrubbing the words...")
        #unwanted_chars = ['?', '!', ',', '.']
        unwanted_chars = "?!.,"
        words = {}
        for chat in inbox.get_selected():
            for message in chat.messages:
                if "content" in message:
                    content = None
                    if not selected_names or (selected_names and message["sender_name"] in selected_names):
                        content = message["content"]
                    if content:
                        # all this formats the individual words so that there are as little duplicate entries as possible
                        #content = (str(filter(lambda ch: ch not in unwanted_chars, fb.remove_diacritic(content.lower())))).split(" ")
                        content = fb.remove_diacritic(content.lower().translate({ord(ch): None for ch in unwanted_chars})).split(" ")
                        for word in content:
                            if len(word) > 1 and len(word) < 20:
                                if word in words:
                                    words[word] += 1
                                else:
                                    words[word] = 1

        print(f"\nThere are {len(words)} unique words")
        limit = int(input("Type \"0\" to save all or specify the ammount: "))
        if limit == 0 or limit > len(words): limit = len(words)

        print("Sorting the words...")
        words_sorted = {}
        for i in tqdm(range(limit)):
            max = 0
            max_key = ""
            for word in words:
                if max < words[word]:
                    max = words[word]
                    max_key = word
            words.pop(max_key)
            words_sorted[max_key] = max
        
        print(f"\nWriting {len(words_sorted)} words to the file")
        with open(list_path, "w", encoding="utf-8") as file_out:
            for i, word in enumerate(words_sorted):
                file_out.write(f'{i}. {word}: {words_sorted[word]}\n')

def main():
    parser = argparse.ArgumentParser(description='Analyze data downloaded from facebook')
    parser.add_argument('-i', dest='path_in', required=True, default='', help='Path to the /inbox/ folder')
    parser.add_argument('-o', dest='path_out', required=False, default='', help='Path to the output folder')

    args = parser.parse_args()
    diags = Dialogs()

    args.path_in = os.path.normpath(args.path_in)
    if args.path_out == "":
        args.path_out = args.path_in[0:args.path_in.index("/messages") + 1]
        print("Path out set to:", args.path_out)
        if not os.access(args.path_out, os.F_OK):
            print("Failed to set the output path automatically, plese use the -o argument to se it manually")
            diags.abort()
    else:
        if not os.access(args.path_out, os.F_OK):
            print("Failed to access the output folder")
            diags.abort()

    print("Loading files...")
    inbox = fb.Inbox(args.path_in)

    diags.output_path = args.path_out
    analyze = Analyze(diags)

    print()
    diags.print_stats_and_times(inbox)

    menu = [
        ("Count messages per timeframe", (analyze.save_graph, inbox)),
        ("Compile a list of most used words", (analyze.save_most_used, inbox)),
        ("Select chats", (diags.select_chats_percentage, inbox)), 
        ("Print statistics", (diags.print_stats_and_times, inbox)), 
        ("Abort", diags.abort)
    ]
    while True:
        print()
        diags.print_numbered_menu_and_execute(menu)
        


if __name__ == '__main__':
    main()