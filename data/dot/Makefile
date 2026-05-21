

all: ebc.pdf ebc-aln.pdf ebc-hr-pos.pdf
	

%.pdf: %.dot
	dot -Tpdf -o $@ $<

clean:
	rm -f *.pdf

