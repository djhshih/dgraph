

all: ebc.pdf ebc-aln.pdf
	

%.pdf: %.dot
	dot -Tpdf -o $@ $<

clean:
	rm -f *.pdf

