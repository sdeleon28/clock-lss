import mido

input_name = "Launchpad Step Sequencer"  # Replace with the name of your MIDI output port

def main():
    with mido.open_input(input_name) as port:
        print(f"Sniffing traffic on {input_name}...")
        for message in port:
            print(message)

if __name__ == '__main__':
    main()
